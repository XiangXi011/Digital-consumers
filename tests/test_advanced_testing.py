import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AdvancedTestingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.ai_clients_path = cls.root / "ai_clients.py"
        cls.advanced_testing_path = cls.root / "advanced_testing.py"
        cls.persona_path = cls.root / "persona_samples_complete.json"

    def load_ai_clients(self):
        if not self.ai_clients_path.exists():
            self.fail("ai_clients.py is missing")
        return load_module("ai_clients_under_test", self.ai_clients_path)

    def load_advanced_testing(self):
        if not self.advanced_testing_path.exists():
            self.fail("advanced_testing.py is missing")
        return load_module("advanced_testing_under_test", self.advanced_testing_path)

    def build_offline_ai_client(self, ai_module):
        class OfflineClient(ai_module.BaseAIClient):
            def __init__(self):
                super().__init__()
                self.is_configured = False

            def generate_text(self, prompt: str, system_prompt: str | None = None) -> dict:
                return {"mode": "fallback_text", "text": "Offline summary"}

            def analyze_image(self, image_path: Path, prompt: str) -> dict:
                return {
                    "mode": "fallback_vision",
                    "text": "Offline vision summary",
                    "structured_signals": {"clarity": "unknown"},
                }

        return OfflineClient()

    def test_ai_client_falls_back_without_api_config(self):
        module = self.load_ai_clients()
        client = module.OpenAICompatibleClient(
            config=module.AIClientConfig(),
            langsmith_config=module.LangSmithConfig(),
        )
        self.assertFalse(client.is_configured)
        text = client.generate_text("Summarize this concept.")
        vision = client.analyze_image(Path("fake.png"), "Describe this packaging.")
        self.assertIn("fallback", text["mode"])
        self.assertIn("fallback", vision["mode"])

    def test_ai_config_can_load_workspace_dotenv(self):
        module = self.load_ai_clients()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dotenv_path = temp_path / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "OPENAI_BASE_URL=https://api.siliconflow.cn/v1",
                        "OPENAI_MODEL=Pro/moonshotai/Kimi-K2.5",
                        "OPENAI_FALLBACK_MODEL=Qwen/Qwen3.5-397B-A17B",
                    ]
                ),
                encoding="utf-8",
            )

            config = module.AIClientConfig.from_env(base_dir=temp_path)

        self.assertEqual(config.api_key, "test-key")
        self.assertEqual(config.base_url, "https://api.siliconflow.cn/v1")
        self.assertEqual(config.model, "Pro/moonshotai/Kimi-K2.5")
        self.assertEqual(config.fallback_model, "Qwen/Qwen3.5-397B-A17B")

    def test_ai_client_exposes_primary_and_fallback_model_nodes(self):
        module = self.load_ai_clients()
        config = module.AIClientConfig(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/moonshotai/Kimi-K2.5",
            fallback_model="Qwen/Qwen3.5-397B-A17B",
        )

        client = module.OpenAICompatibleClient(config=config, langsmith_config=module.LangSmithConfig())

        self.assertEqual(
            client.get_text_model_candidates(),
            ["Pro/moonshotai/Kimi-K2.5", "Qwen/Qwen3.5-397B-A17B"],
        )

    def test_ai_config_normalizes_chat_completions_url(self):
        module = self.load_ai_clients()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dotenv_path = temp_path / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "OPENAI_BASE_URL=https://api.siliconflow.cn/v1/chat/completions",
                        "OPENAI_MODEL=Pro/moonshotai/Kimi-K2.5",
                    ]
                ),
                encoding="utf-8",
            )

            config = module.AIClientConfig.from_env(base_dir=temp_path)

        self.assertEqual(config.base_url, "https://api.siliconflow.cn/v1")

    def test_ai_config_can_disable_vision_model(self):
        module = self.load_ai_clients()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            dotenv_path = temp_path / ".env"
            dotenv_path.write_text(
                "\n".join(
                    [
                        "OPENAI_API_KEY=test-key",
                        "OPENAI_BASE_URL=https://api.siliconflow.cn/v1",
                        "OPENAI_MODEL=Pro/moonshotai/Kimi-K2.5",
                        "OPENAI_VISION_MODEL=disabled",
                    ]
                ),
                encoding="utf-8",
            )

            config = module.AIClientConfig.from_env(base_dir=temp_path)

        self.assertEqual(config.vision_model, "")

    def test_ai_client_uses_fallback_model_when_primary_fails(self):
        module = self.load_ai_clients()

        class FakeCompletions:
            def __init__(self):
                self.calls = []

            def create(self, model, messages):
                self.calls.append(model)
                if model == "Pro/moonshotai/Kimi-K2.5":
                    raise RuntimeError("primary unavailable")
                return type(
                    "FakeResponse",
                    (),
                    {
                        "choices": [
                            type(
                                "FakeChoice",
                                (),
                                {
                                    "message": type(
                                        "FakeMessage",
                                        (),
                                        {"content": "fallback model response"},
                                    )()
                                },
                            )()
                        ]
                    },
                )()

        fake_completions = FakeCompletions()
        fake_client = type(
            "FakeClient",
            (),
            {"chat": type("FakeChat", (), {"completions": fake_completions})()},
        )()
        config = module.AIClientConfig(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/moonshotai/Kimi-K2.5",
            fallback_model="Qwen/Qwen3.5-397B-A17B",
        )
        client = module.OpenAICompatibleClient(config=config, langsmith_config=module.LangSmithConfig())
        client.client = fake_client

        result = client.generate_text("Summarize this concept.")

        self.assertEqual(fake_completions.calls, ["Pro/moonshotai/Kimi-K2.5", "Qwen/Qwen3.5-397B-A17B"])
        self.assertEqual(result["mode"], "live_text")
        self.assertEqual(result["model"], "Qwen/Qwen3.5-397B-A17B")
        self.assertEqual(result["text"], "fallback model response")

    def test_ai_client_falls_back_when_vision_request_errors(self):
        module = self.load_ai_clients()

        class FakeCompletions:
            def create(self, model, messages):
                raise RuntimeError(f"{model} is not a vision model")

        fake_client = type(
            "FakeClient",
            (),
            {"chat": type("FakeChat", (), {"completions": FakeCompletions()})()},
        )()
        config = module.AIClientConfig(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/moonshotai/Kimi-K2.5",
            vision_model="Pro/moonshotai/Kimi-K2.5",
            ocr_base_url="",
        )
        client = module.OpenAICompatibleClient(config=config, langsmith_config=module.LangSmithConfig())
        client.client = fake_client

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "packaging.png"
            Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image_path)
            result = client.analyze_image(image_path, "Describe this packaging.")

        self.assertEqual(result["mode"], "fallback_vision")
        self.assertIn("errors", result)

    def test_ai_client_skips_remote_vision_when_vision_model_disabled(self):
        module = self.load_ai_clients()
        config = module.AIClientConfig(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/moonshotai/Kimi-K2.5",
            vision_model="",
        )
        client = module.OpenAICompatibleClient(config=config, langsmith_config=module.LangSmithConfig())

        class FakeCompletions:
            def create(self, model, messages):
                raise AssertionError("vision API should not be called when disabled")

        client.client = type(
            "FakeClient",
            (),
            {"chat": type("FakeChat", (), {"completions": FakeCompletions()})()},
        )()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "packaging.png"
            Image.new("RGB", (32, 32), color=(255, 255, 255)).save(image_path)
            result = client.analyze_image(image_path, "Describe this packaging.")

        self.assertEqual(result["mode"], "fallback_vision")
        self.assertIn("disabled", result["text"])

    def test_tall_image_extraction_merges_fields_from_multiple_tiles(self):
        module = self.load_ai_clients()
        config = module.AIClientConfig(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/moonshotai/Kimi-K2.5",
            vision_model="Pro/moonshotai/Kimi-K2.5",
            ocr_base_url="",
        )
        client = module.OpenAICompatibleClient(config=config, langsmith_config=module.LangSmithConfig())

        calls = []
        payloads = iter(
            [
                "{\"concept_name\":\"舒客宝贝魔法变色儿童牙膏\",\"brand\":\"舒客宝贝\",\"category\":\"儿童牙膏\",\"core_claims\":[\"健白抗糖防蛀\",\"12小时长效防蛀\"],\"price\":\"\",\"packaging_summary\":\"粉蓝渐变软管包装\"}",
                "{\"concept_name\":\"\",\"brand\":\"\",\"category\":\"\",\"core_claims\":[\"超20项安全测试\"],\"price\":\"39.9元\",\"packaging_summary\":\"\"}",
            ]
        )

        def fake_create_vision_completion(image_path, prompt):
            calls.append(image_path)
            return type(
                "FakeResponse",
                (),
                {
                    "choices": [
                        type(
                            "FakeChoice",
                            (),
                            {
                                "message": type(
                                    "FakeMessage",
                                    (),
                                    {"content": next(payloads)},
                                )()
                            },
                        )()
                    ]
                },
            )()

        client._create_vision_completion = fake_create_vision_completion

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "tall-detail.png"
            Image.new("RGB", (1200, 9000), color=(255, 255, 255)).save(image_path)
            result = client.extract_product_fields_from_image(image_path)

        self.assertGreaterEqual(len(calls), 2)
        self.assertEqual(result["mode"], "live_vision_extraction")
        self.assertEqual(result["fields"]["concept_name"], "舒客宝贝魔法变色儿童牙膏")
        self.assertEqual(result["fields"]["price"], "39.9元")
        self.assertIn("超20项安全测试", result["fields"]["core_claims"])

    def test_image_extraction_prefers_ocr_text_path_before_vision(self):
        module = self.load_ai_clients()

        class OCRFirstClient(module.OpenAICompatibleClient):
            def __init__(self, config):
                super().__init__(config=config)
                self.vision_calls = 0

            def _extract_ocr_text(self, image_path):
                return (
                    "产品名称：舒客宝贝魔法变色儿童牙膏\n"
                    "儿童牙膏\n"
                    "健白抗糖防蛀\n"
                    "12小时长效防蛀\n"
                    "超20项安全测试\n"
                )

            def generate_text(self, prompt: str, system_prompt: str | None = None) -> dict:
                return {
                    "mode": "live_text",
                    "text": (
                        "{\"concept_name\":\"舒客宝贝魔法变色儿童牙膏\","
                        "\"brand\":\"舒客宝贝\","
                        "\"category\":\"儿童牙膏\","
                        "\"core_claims\":[\"健白抗糖防蛀\",\"12小时长效防蛀\",\"超20项安全测试\"],"
                        "\"price\":\"\","
                        "\"packaging_summary\":\"儿童牙膏详情页，重点突出防蛀与安全测试。\"}"
                    ),
                }

            def _create_vision_completion(self, image_path, prompt):
                self.vision_calls += 1
                raise AssertionError("vision extraction should not run when OCR path already succeeded")

        config = module.AIClientConfig(
            api_key="test-key",
            base_url="https://api.siliconflow.cn/v1",
            model="Pro/moonshotai/Kimi-K2.5",
            vision_model="Pro/moonshotai/Kimi-K2.5",
        )
        client = OCRFirstClient(config=config)

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "detail-page.png"
            Image.new("RGB", (800, 2400), color=(255, 255, 255)).save(image_path)
            result = client.extract_product_fields_from_image(image_path)

        self.assertEqual(result["mode"], "live_ocr_extraction")
        self.assertEqual(result["fields"]["concept_name"], "舒客宝贝魔法变色儿童牙膏")
        self.assertEqual(result["fields"]["category"], "儿童牙膏")
        self.assertEqual(client.vision_calls, 0)

    def test_ab_comparison_report_has_winner_and_deltas(self):
        ai_module = self.load_ai_clients()
        module = self.load_advanced_testing()
        runner = module.AdvancedTestRunner(self.persona_path, ai_client=self.build_offline_ai_client(ai_module))
        concept_a, concept_b = module.build_sample_ab_inputs()

        report = runner.run_ab_comparison(concept_a, concept_b)

        self.assertIn("variant_a", report)
        self.assertIn("variant_b", report)
        self.assertIn("winner", report)
        self.assertIn(report["winner"], {"A", "B", "tie"})
        self.assertIn("segment_deltas", report)
        self.assertTrue(report["segment_deltas"])

    def test_price_ladder_report_returns_price_points_and_recommendation(self):
        ai_module = self.load_ai_clients()
        module = self.load_advanced_testing()
        runner = module.AdvancedTestRunner(self.persona_path, ai_client=self.build_offline_ai_client(ai_module))
        concept = module.build_sample_single_input()

        report = runner.run_price_ladder(concept, [29.9, 39.9, 49.9, 59.9])

        self.assertEqual(len(report["price_points"]), 4)
        self.assertEqual([item["price"] for item in report["price_points"]], [29.9, 39.9, 49.9, 59.9])
        self.assertIn("recommended_price_zone", report)
        self.assertIn("drop_off_point", report)

    def test_packaging_review_accepts_local_image_path(self):
        ai_module = self.load_ai_clients()
        module = self.load_advanced_testing()
        runner = module.AdvancedTestRunner(self.persona_path, ai_client=self.build_offline_ai_client(ai_module))
        concept = module.build_sample_single_input()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "packaging.png"
            Image.new("RGB", (120, 120), color=(255, 120, 80)).save(image_path)

            report = runner.run_packaging_review(concept, image_path)

        self.assertIn("packaging_review", report)
        self.assertIn("visual_summary", report["packaging_review"])
        self.assertIn("structured_signals", report["packaging_review"])
        self.assertIn("single_concept_report", report)

    def test_text_generator_hook_can_enhance_report_language(self):
        ai_module = self.load_ai_clients()
        advanced_module = self.load_advanced_testing()

        class StubClient(ai_module.BaseAIClient):
            def __init__(self):
                super().__init__()
                self.is_configured = True

            def generate_text(self, prompt: str, system_prompt: str | None = None) -> dict:
                return {"mode": "stub", "text": "LLM enhanced summary"}

            def analyze_image(self, image_path: Path, prompt: str) -> dict:
                return {
                    "mode": "stub",
                    "text": "Visual summary",
                    "structured_signals": {"clarity": "high"},
                }

        runner = advanced_module.AdvancedTestRunner(self.persona_path, ai_client=StubClient())
        report = runner.run_single_concept_with_ai(advanced_module.build_sample_single_input())

        self.assertEqual(report["executive_summary"]["llm_summary"], "LLM enhanced summary")

    def test_advanced_runner_is_backed_by_graph_based_single_concept_runner(self):
        ai_module = self.load_ai_clients()
        advanced_module = self.load_advanced_testing()

        runner = advanced_module.AdvancedTestRunner(self.persona_path, ai_client=self.build_offline_ai_client(ai_module))

        self.assertTrue(hasattr(runner, "runner"))
        self.assertTrue(hasattr(runner.runner, "analysis_graph"))
        self.assertIsNotNone(runner.runner.analysis_graph)

    def test_langsmith_config_can_load_workspace_dotenv(self):
        module = self.load_ai_clients()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".env").write_text(
                "\n".join(
                    [
                        "LANGSMITH_TRACING=true",
                        "LANGSMITH_ENDPOINT=https://api.smith.langchain.com",
                        "LANGSMITH_API_KEY=test-langsmith-key",
                        "LANGSMITH_PROJECT=数字消费者",
                    ]
                ),
                encoding="utf-8",
            )

            config = module.LangSmithConfig.from_env(base_dir=temp_path)

        self.assertTrue(config.tracing_enabled)
        self.assertEqual(config.endpoint, "https://api.smith.langchain.com")
        self.assertEqual(config.api_key, "test-langsmith-key")
        self.assertEqual(config.project, "数字消费者")
        self.assertTrue(config.is_enabled)

    def test_langsmith_tracing_stays_disabled_without_api_key(self):
        module = self.load_ai_clients()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / ".env").write_text(
                "\n".join(
                    [
                        "LANGSMITH_TRACING=true",
                        "LANGSMITH_ENDPOINT=https://api.smith.langchain.com",
                        "LANGSMITH_PROJECT=数字消费者",
                    ]
                ),
                encoding="utf-8",
            )

            config = module.LangSmithConfig.from_env(base_dir=temp_path)

        self.assertTrue(config.tracing_enabled)
        self.assertEqual(config.api_key, "")
        self.assertFalse(config.is_enabled)

    def test_traced_quote_and_validation_calls_keep_return_shape(self):
        module = self.load_ai_clients()

        class TracedClient(module.OpenAICompatibleClient):
            def __init__(self, config, langsmith_config):
                super().__init__(config=config)
                self.langsmith_config = langsmith_config

            def generate_text(self, prompt: str, system_prompt: str | None = None) -> dict:
                if "is_consistent" in prompt:
                    return {
                        "mode": "live_text",
                        "text": '{"is_consistent": true, "detected_stance": "犹豫者", "detected_reason": "安全感不足", "why": "quote 明确表达仍需确认安全性"}',
                    }
                return {
                    "mode": "live_text",
                    "text": '{"quote": "孩子应该会喜欢变色，但我还是想先确认低龄使用是不是足够安全。"}',
                }

        langsmith_config = module.LangSmithConfig(
            tracing_enabled=True,
            endpoint="https://api.smith.langchain.com",
            api_key="test-langsmith-key",
            project="数字消费者",
        )
        client = TracedClient(
            config=module.AIClientConfig(
                api_key="test-key",
                base_url="https://api.siliconflow.cn/v1",
                model="Pro/moonshotai/Kimi-K2.5",
            ),
            langsmith_config=langsmith_config,
        )

        original_traceable = module._langsmith_traceable
        module._langsmith_traceable = lambda **kwargs: (lambda func: func)
        try:
            self.assertTrue(client.langsmith_config.is_enabled)

            quote = client.generate_consumer_quote(
                {
                    "agent_name": "林可可",
                    "segment": "宠爱富养家",
                    "stance_label": "犹豫者",
                    "reason_tag": "安全感不足",
                    "purchase_intention": 0.48,
                    "decision": "consider",
                    "reasoning": "孩子会喜欢，但我还想确认更具体的安全依据。",
                    "key_concerns": ["含氟安全性"],
                    "preferred_features": ["趣味刷牙"],
                    "discussion_signal": "有趣但仍需确认安全",
                    "deep_dive_signal": "担心低龄儿童误吞",
                }
            )
            validation = client.validate_consumer_quote("犹豫者", "安全感不足", quote["quote"])
        finally:
            module._langsmith_traceable = original_traceable

        self.assertEqual(quote["mode"], "live_text")
        self.assertIsInstance(quote["quote"], str)
        self.assertTrue(quote["quote"])
        self.assertEqual(validation["mode"], "live_text")
        self.assertTrue(validation["is_consistent"])
        self.assertEqual(validation["detected_stance"], "犹豫者")
        self.assertEqual(validation["detected_reason"], "安全感不足")

    def test_remote_ocr_path_works_with_tracing_enabled(self):
        module = self.load_ai_clients()
        langsmith_config = module.LangSmithConfig(
            tracing_enabled=True,
            endpoint="https://api.smith.langchain.com",
            api_key="test-langsmith-key",
            project="数字消费者",
        )
        client = module.OpenAICompatibleClient(
            config=module.AIClientConfig(
                api_key="test-key",
                base_url="https://api.siliconflow.cn/v1",
                model="Pro/moonshotai/Kimi-K2.5",
                ocr_base_url="http://127.0.0.1:18080/v1",
                ocr_model="glm-ocr",
            ),
            langsmith_config=langsmith_config,
        )

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    "choices": [
                        {
                            "message": {
                                "content": "产品名称：舒客宝贝魔法变色儿童牙膏\n价格：28元一支\n"
                            }
                        }
                    ]
                }

        original_post = module.requests.post
        original_traceable = module._langsmith_traceable

        def fake_post(url, json, timeout):
            return FakeResponse()

        module._langsmith_traceable = lambda **kwargs: (lambda func: func)
        module.requests.post = fake_post
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                image_path = Path(temp_dir) / "ocr-test.jpg"
                Image.new("RGB", (64, 64), color=(255, 255, 255)).save(image_path)
                text = client._extract_ocr_text_via_remote(image_path)
        finally:
            module._langsmith_traceable = original_traceable
            module.requests.post = original_post

        self.assertTrue(client.langsmith_config.is_enabled)
        self.assertIn("舒客宝贝魔法变色儿童牙膏", text)
        self.assertIn("28元一支", text)


if __name__ == "__main__":
    unittest.main()
