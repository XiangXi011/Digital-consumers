import importlib.util
import os
import tempfile
import unittest
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image


def load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="vision ok"),
                )
            ]
        )


class FakeOpenAI:
    instances = []

    def __init__(self, api_key=None, base_url=None, timeout=None, max_retries=None):
        self.api_key = api_key
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.chat = SimpleNamespace(completions=FakeCompletions())
        FakeOpenAI.instances.append(self)


class FakeDashScope:
    def __init__(self):
        self.base_http_api_url = None
        self.calls = []
        self.response_text = "vision ok"
        self.status_code = HTTPStatus.OK
        self.MultiModalConversation = SimpleNamespace(call=self.call)

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            status_code=self.status_code,
            request_id="fake-request-id",
            output=SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            content=[{"text": self.response_text}],
                        )
                    )
                ]
            ),
        )


class AIClientsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1]
        cls.module_path = cls.root / "ai_clients.py"

    def setUp(self):
        FakeOpenAI.instances = []

    def load_or_fail(self):
        if not self.module_path.exists():
            self.fail("ai_clients.py is missing")
        return load_module("ai_clients_under_test", self.module_path)

    def write_dotenv(self, temp_dir: str, lines: list[str]) -> Path:
        path = Path(temp_dir) / ".env"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def create_image(self, temp_dir: str) -> Path:
        path = Path(temp_dir) / "sample.png"
        Image.new("RGB", (16, 16), color="white").save(path)
        return path

    def test_from_env_reads_dashscope_vision_settings(self):
        module = self.load_or_fail()

        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_dotenv(
                temp_dir,
                [
                    "OPENAI_API_KEY=text-key",
                    "OPENAI_BASE_URL=https://text.example.com/v1",
                    "OPENAI_MODEL=text-model",
                    "DASHSCOPE_API_KEY=dash-key",
                    "DASHSCOPE_VISION_MODEL=qwen3.5-plus",
                ],
            )

            with patch.dict(os.environ, {}, clear=True):
                config = module.AIClientConfig.from_env(Path(temp_dir))

        self.assertEqual(config.api_key, "text-key")
        self.assertEqual(config.base_url, "https://text.example.com/v1")
        self.assertEqual(config.vision_api_key, "dash-key")
        self.assertEqual(config.vision_base_url, "https://dashscope.aliyuncs.com/api/v1")
        self.assertEqual(config.vision_model, "qwen3.5-plus")

    def test_from_env_prefers_workspace_dashscope_key_over_process_env(self):
        module = self.load_or_fail()

        with tempfile.TemporaryDirectory() as temp_dir:
            self.write_dotenv(
                temp_dir,
                [
                    "OPENAI_API_KEY=text-key",
                    "DASHSCOPE_API_KEY=dash-key-from-dotenv",
                    "DASHSCOPE_VISION_MODEL=qwen3.5-plus",
                ],
            )

            with patch.dict(os.environ, {"DASHSCOPE_API_KEY": "stale-process-key"}, clear=True):
                config = module.AIClientConfig.from_env(Path(temp_dir))

        self.assertEqual(config.vision_api_key, "dash-key-from-dotenv")

    def test_analyze_image_uses_dashscope_multimodal_conversation(self):
        module = self.load_or_fail()
        fake_dashscope = FakeDashScope()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = self.create_image(temp_dir)
            with patch.object(module, "OpenAI", FakeOpenAI), patch.object(module, "dashscope", fake_dashscope):
                client = module.OpenAICompatibleClient(
                    config=module.AIClientConfig(
                        vision_api_key="dash-key",
                        vision_base_url="https://dashscope.aliyuncs.com/api/v1",
                        vision_model="qwen3.5-plus",
                        timeout_seconds=45.0,
                    )
                )

                result = client.analyze_image(image_path, "What is this image?")

        self.assertEqual(len(FakeOpenAI.instances), 0)
        self.assertEqual(fake_dashscope.base_http_api_url, "https://dashscope.aliyuncs.com/api/v1")
        self.assertEqual(len(fake_dashscope.calls), 1)
        self.assertEqual(fake_dashscope.calls[0]["api_key"], "dash-key")
        self.assertEqual(fake_dashscope.calls[0]["model"], "qwen3.5-plus")
        self.assertEqual(fake_dashscope.calls[0]["messages"][0]["role"], "user")
        self.assertIn("text", fake_dashscope.calls[0]["messages"][0]["content"][1])
        self.assertTrue(fake_dashscope.calls[0]["messages"][0]["content"][0]["image"].startswith("data:image/"))
        self.assertEqual(result["mode"], "live_vision")
        self.assertEqual(result["model"], "qwen3.5-plus")

    def test_extract_product_fields_from_image_uses_dashscope_multimodal_conversation(self):
        module = self.load_or_fail()
        fake_dashscope = FakeDashScope()
        fake_dashscope.response_text = (
            '{"concept_name":"测试牙膏","brand":"测试品牌","category":"儿童牙膏","core_claims":["低氟防蛀"],'
            '"price":"39元","packaging_summary":"儿童牙膏包装","target_channels":[],"target_audience":"3-12岁",'
            '"competitors":[],"slogan":"","ingredients":"","detail_copy":"","validation_questions":""}'
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = self.create_image(temp_dir)
            with patch.object(module, "dashscope", fake_dashscope):
                client = module.OpenAICompatibleClient(
                    config=module.AIClientConfig(
                        vision_api_key="dash-key",
                        vision_base_url="https://dashscope.aliyuncs.com/api/v1",
                        vision_model="qwen3.5-plus",
                        timeout_seconds=45.0,
                        ocr_base_url=None,
                    )
                )

                result = client.extract_product_fields_from_image(image_path)

        self.assertEqual(len(fake_dashscope.calls), 1)
        self.assertEqual(result["mode"], "live_vision_extraction")
        self.assertEqual(result["model"], "qwen3.5-plus")
        self.assertEqual(result["fields"]["concept_name"], "测试牙膏")
        self.assertEqual(result["fields"]["price"], "39元")

    def test_analyze_image_falls_back_when_dashscope_sdk_is_unavailable(self):
        module = self.load_or_fail()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = self.create_image(temp_dir)
            with patch.object(module, "dashscope", None):
                client = module.OpenAICompatibleClient(
                    config=module.AIClientConfig(
                        vision_api_key="dash-key",
                        vision_base_url="https://dashscope.aliyuncs.com/api/v1",
                        vision_model="qwen3.5-plus",
                        timeout_seconds=45.0,
                    )
                )

                result = client.analyze_image(image_path, "What is this image?")

        self.assertEqual(result["mode"], "fallback_vision")
        self.assertIn("DashScope SDK is unavailable", result["text"])


if __name__ == "__main__":
    unittest.main()
