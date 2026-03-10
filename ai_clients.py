import base64
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from openai import OpenAI
from PIL import Image
import requests

try:
    from langsmith import traceable as _langsmith_traceable
except Exception:  # pragma: no cover - optional dependency
    _langsmith_traceable = None

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:  # pragma: no cover - optional dependency
    RapidOCR = None


def _load_workspace_dotenv(base_dir: Path) -> Dict[str, str]:
    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return {}

    values: Dict[str, str] = {}
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _normalize_openai_base_url(base_url: Optional[str]) -> Optional[str]:
    if not base_url:
        return base_url

    normalized = base_url.rstrip("/")
    suffix = "/chat/completions"
    if normalized.endswith(suffix):
        normalized = normalized[: -len(suffix)]
    return normalized


def _get_config_value(name: str, dotenv_values: Dict[str, str], default: str = "") -> str:
    if name in os.environ:
        return os.environ[name]
    if name in dotenv_values:
        return dotenv_values[name]
    return default


def _is_truthy_flag(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class AIClientConfig:
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "gpt-4.1-mini"
    fallback_model: str = ""
    vision_model: str = "gpt-4.1-mini"
    timeout_seconds: float = 30.0
    ocr_base_url: Optional[str] = "http://192.168.118.80:18080/v1"
    ocr_model: str = "glm-ocr"
    ocr_timeout_seconds: float = 120.0

    @classmethod
    def from_env(cls, base_dir: Path | None = None):
        dotenv_values = _load_workspace_dotenv(base_dir or Path.cwd())
        timeout_raw = _get_config_value("OPENAI_TIMEOUT_SECONDS", dotenv_values, "30")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError:
            timeout_seconds = 30.0
        ocr_timeout_raw = _get_config_value("OCR_TIMEOUT_SECONDS", dotenv_values, "120")
        try:
            ocr_timeout_seconds = float(ocr_timeout_raw)
        except ValueError:
            ocr_timeout_seconds = 120.0

        default_model = _get_config_value("OPENAI_MODEL", dotenv_values, "gpt-4.1-mini")
        vision_model_raw = _get_config_value("OPENAI_VISION_MODEL", dotenv_values, default_model)
        if vision_model_raw.strip().lower() in {"", "disabled", "none", "off"}:
            vision_model = ""
        else:
            vision_model = vision_model_raw

        return cls(
            api_key=_get_config_value("OPENAI_API_KEY", dotenv_values, ""),
            base_url=_normalize_openai_base_url(_get_config_value("OPENAI_BASE_URL", dotenv_values, "")) or None,
            model=default_model,
            fallback_model=_get_config_value("OPENAI_FALLBACK_MODEL", dotenv_values, ""),
            vision_model=vision_model,
            timeout_seconds=timeout_seconds,
            ocr_base_url=_normalize_openai_base_url(
                _get_config_value("OCR_BASE_URL", dotenv_values, "http://192.168.118.80:18080/v1")
            )
            or None,
            ocr_model=_get_config_value("OCR_MODEL", dotenv_values, "glm-ocr"),
            ocr_timeout_seconds=ocr_timeout_seconds,
        )


@dataclass
class LangSmithConfig:
    tracing_enabled: bool = False
    endpoint: str = "https://api.smith.langchain.com"
    api_key: str = ""
    project: str = "数字消费者"

    @property
    def is_enabled(self) -> bool:
        return self.tracing_enabled and bool(self.api_key)

    @classmethod
    def from_env(cls, base_dir: Path | None = None):
        dotenv_values = _load_workspace_dotenv(base_dir or Path.cwd())
        return cls(
            tracing_enabled=_is_truthy_flag(_get_config_value("LANGSMITH_TRACING", dotenv_values, "false")),
            endpoint=_get_config_value("LANGSMITH_ENDPOINT", dotenv_values, "https://api.smith.langchain.com"),
            api_key=_get_config_value("LANGSMITH_API_KEY", dotenv_values, ""),
            project=_get_config_value("LANGSMITH_PROJECT", dotenv_values, "数字消费者"),
        )


class BaseAIClient:
    def __init__(self, langsmith_config: LangSmithConfig | None = None):
        self.is_configured = False
        self.langsmith_config = langsmith_config or LangSmithConfig.from_env()

    def _apply_langsmith_environment(self) -> None:
        if not self.langsmith_config.is_enabled:
            return
        os.environ["LANGSMITH_TRACING"] = "true"
        if self.langsmith_config.endpoint:
            os.environ["LANGSMITH_ENDPOINT"] = self.langsmith_config.endpoint
        if self.langsmith_config.api_key:
            os.environ["LANGSMITH_API_KEY"] = self.langsmith_config.api_key
        if self.langsmith_config.project:
            os.environ["LANGSMITH_PROJECT"] = self.langsmith_config.project

    def _run_with_optional_trace(
        self,
        name: str,
        run_type: str,
        operation: Callable[[], Any],
        trace_inputs: Dict[str, Any] | None = None,
    ) -> Any:
        if not self.langsmith_config.is_enabled or _langsmith_traceable is None:
            return operation()

        self._apply_langsmith_environment()
        safe_inputs = trace_inputs or {}
        try:
            traced_operation = _langsmith_traceable(name=name, run_type=run_type)(lambda **_: operation())
            return traced_operation(**safe_inputs)
        except Exception:
            return operation()

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        raise NotImplementedError

    def analyze_image(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        raise NotImplementedError

    def extract_product_fields_from_image(self, image_path: Path) -> Dict[str, Any]:
        return {
            "mode": "fallback_vision_extraction",
            "fields": {},
            "raw_text": "",
        }

    def generate_consumer_quote(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "mode": "fallback_quote",
            "quote": "",
            "reason": "AI quote generation is unavailable.",
        }

    def validate_consumer_quote(
        self,
        expected_stance: str,
        expected_reason_tag: str,
        quote: str,
    ) -> Dict[str, Any]:
        return {
            "mode": "fallback_validation",
            "is_consistent": False,
            "detected_stance": "",
            "detected_reason": "",
            "why": "AI quote validation is unavailable.",
        }


def _extract_json_object(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, flags=re.DOTALL)
    candidate = fenced_match.group(1) if fenced_match else text

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return {}

    try:
        return json.loads(candidate[start : end + 1])
    except json.JSONDecodeError:
        return {}


def _extract_quote_candidate(text: str) -> str:
    if not text:
        return ""

    candidate = text.strip()
    candidate = re.sub(r"```(?:json)?", "", candidate, flags=re.IGNORECASE).replace("```", "").strip()

    quote_match = re.search(r'"quote"\s*:\s*"([^"]+)"', candidate)
    if quote_match:
        return quote_match.group(1).strip()

    line_match = re.search(r"(?:quote|原声)\s*[:：]\s*(.+)", candidate, flags=re.IGNORECASE)
    if line_match:
        return line_match.group(1).strip().strip('"')

    first_line = next((line.strip() for line in candidate.splitlines() if line.strip()), "")
    return first_line.strip('"')


def _extract_validation_candidate(text: str) -> Dict[str, Any]:
    if not text:
        return {}

    candidate = text.strip()
    candidate = re.sub(r"```(?:json)?", "", candidate, flags=re.IGNORECASE).replace("```", "").strip()
    parsed = _extract_json_object(candidate)
    if parsed:
        return parsed

    result: Dict[str, Any] = {}
    consistency_match = re.search(r"(?:is_consistent|consistent)\s*[:：]\s*(true|false)", candidate, flags=re.IGNORECASE)
    if consistency_match:
        result["is_consistent"] = consistency_match.group(1).lower() == "true"

    stance_match = re.search(r"(?:detected_stance|stance)\s*[:：]\s*([^\n,，]+)", candidate, flags=re.IGNORECASE)
    if stance_match:
        result["detected_stance"] = stance_match.group(1).strip().strip('"')

    reason_match = re.search(r"(?:detected_reason|reason)\s*[:：]\s*([^\n,，]+)", candidate, flags=re.IGNORECASE)
    if reason_match:
        result["detected_reason"] = reason_match.group(1).strip().strip('"')

    why_match = re.search(r"(?:why)\s*[:：]\s*(.+)", candidate, flags=re.IGNORECASE)
    if why_match:
        result["why"] = why_match.group(1).strip().strip('"')

    return result


def _normalize_extracted_fields(raw_fields: Dict[str, Any]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    list_fields = {"core_claims", "target_channels", "competitors"}

    for key, value in raw_fields.items():
        if key == "confidence":
            continue
        if key in list_fields:
            if isinstance(value, list):
                normalized[key] = [str(item).strip() for item in value if str(item).strip()]
            elif isinstance(value, str):
                normalized[key] = [item.strip() for item in re.split(r"[，,；;、\n]", value) if item.strip()]
            else:
                normalized[key] = []
            continue

        if isinstance(value, list):
            normalized[key] = "，".join(str(item).strip() for item in value if str(item).strip())
        elif value is None:
            normalized[key] = ""
        else:
            normalized[key] = str(value).strip()

    return normalized


def _has_core_extracted_fields(fields: Dict[str, Any]) -> bool:
    return bool(
        fields.get("concept_name")
        and fields.get("category")
        and fields.get("core_claims")
        and fields.get("price")
        and fields.get("packaging_summary")
    )


def _count_present_core_fields(fields: Dict[str, Any]) -> int:
    keys = ("concept_name", "category", "core_claims", "price", "packaging_summary")
    return sum(1 for key in keys if fields.get(key))


class OpenAICompatibleClient(BaseAIClient):
    def __init__(
        self,
        config: AIClientConfig | None = None,
        langsmith_config: LangSmithConfig | None = None,
    ):
        super().__init__(langsmith_config=langsmith_config)
        self.config = config or AIClientConfig.from_env()
        self.is_configured = bool(self.config.api_key)
        self.client = None
        self._ocr_engine = None
        self._ocr_unavailable = RapidOCR is None

        if self.is_configured:
            self.client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
                max_retries=0,
            )

    def get_text_model_candidates(self) -> list[str]:
        candidates = [self.config.model]
        if self.config.fallback_model and self.config.fallback_model not in candidates:
            candidates.append(self.config.fallback_model)
        return candidates

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> Dict[str, Any]:
        def execute() -> Dict[str, Any]:
            if not self.is_configured or not self.client:
                return {
                    "mode": "fallback_text",
                    "text": "Fallback summary: API configuration is missing, so local deterministic text was used.",
                }

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            errors: list[str] = []
            for model_name in self.get_text_model_candidates():
                try:
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                    )
                    return {
                        "mode": "live_text",
                        "model": model_name,
                        "text": response.choices[0].message.content or "",
                    }
                except Exception as exc:  # pragma: no cover - exercised through tests
                    errors.append(f"{model_name}: {exc}")

            return {
                "mode": "fallback_text",
                "text": "Fallback summary: remote text generation failed, so local deterministic text was used.",
                "errors": errors,
            }

        return self._run_with_optional_trace(
            name="ai.generate_text",
            run_type="llm",
            operation=execute,
            trace_inputs={
                "prompt_preview": prompt[:600],
                "system_prompt_preview": (system_prompt or "")[:300],
                "model_candidates": ",".join(self.get_text_model_candidates()),
            },
        )

    def generate_consumer_quote(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        def execute() -> Dict[str, Any]:
            prompt = "\n".join(
                [
                    "请基于以下结构化信息生成一条消费者原声。",
                    "要求：",
                    "1. 只输出 JSON，不要输出解释。",
                    "2. JSON 结构固定为 {\"quote\": \"...\"}。",
                    "3. 只写一句中文原声，18-40 个字优先。",
                    "4. 必须符合给定 stance，不要写分析师口吻。",
                    "5. 支持者要体现愿意尝试；犹豫者要体现仍需确认；拒绝者要体现暂不买。",
                    "",
                    f"姓名：{payload.get('agent_name', '')}",
                    f"人群：{payload.get('segment', '')}",
                    f"预期立场：{payload.get('stance_label', '')}",
                    f"原因标签：{payload.get('reason_tag', '')}",
                    f"购买意向：{payload.get('purchase_intention', '')}",
                    f"决策：{payload.get('decision', '')}",
                    f"推理：{payload.get('reasoning', '')}",
                    f"顾虑：{json.dumps(payload.get('key_concerns', []), ensure_ascii=False)}",
                    f"偏好：{json.dumps(payload.get('preferred_features', []), ensure_ascii=False)}",
                    f"讨论信号：{payload.get('discussion_signal', '')}",
                    f"深访信号：{payload.get('deep_dive_signal', '')}",
                ]
            )
            result = self.generate_text(
                prompt=prompt,
                system_prompt="你是消费洞察研究员，请输出严格 JSON。",
            )
            parsed = _extract_json_object(result.get("text", ""))
            quote = str(parsed.get("quote", "")).strip()
            if not quote and str(result.get("mode", "")).startswith("live"):
                quote = _extract_quote_candidate(result.get("text", ""))
            if not quote:
                return {
                    "mode": "fallback_quote",
                    "quote": "",
                    "reason": "Failed to parse quote JSON.",
                    "raw_mode": result.get("mode", ""),
                    "raw_text": result.get("text", ""),
                }
            return {
                "mode": result.get("mode", "live_quote"),
                "quote": quote,
            }

        return self._run_with_optional_trace(
            name="ai.generate_consumer_quote",
            run_type="llm",
            operation=execute,
            trace_inputs={
                "agent_name": str(payload.get("agent_name", "")),
                "segment": str(payload.get("segment", "")),
                "stance_label": str(payload.get("stance_label", "")),
                "reason_tag": str(payload.get("reason_tag", "")),
            },
        )

    def validate_consumer_quote(
        self,
        expected_stance: str,
        expected_reason_tag: str,
        quote: str,
    ) -> Dict[str, Any]:
        def execute() -> Dict[str, Any]:
            prompt = "\n".join(
                [
                    "请判断下面这句消费者原声是否与预期立场一致。",
                    "要求：",
                    "1. 只输出 JSON，不要输出解释。",
                    "2. JSON 结构固定为 {\"is_consistent\": true/false, \"detected_stance\": \"...\", \"detected_reason\": \"...\", \"why\": \"...\"}。",
                    "3. 只根据 quote 本身判断，不要迎合预期。",
                    "",
                    f"预期立场：{expected_stance}",
                    f"预期原因标签：{expected_reason_tag}",
                    f"quote：{quote}",
                ]
            )
            result = self.generate_text(
                prompt=prompt,
                system_prompt="你是消费者原声质检器，请输出严格 JSON。",
            )
            parsed = _extract_validation_candidate(result.get("text", ""))
            if "is_consistent" not in parsed:
                return {
                    "mode": "fallback_validation",
                    "is_consistent": False,
                    "detected_stance": "",
                    "detected_reason": "",
                    "why": "Failed to parse validation JSON.",
                    "raw_mode": result.get("mode", ""),
                    "raw_text": result.get("text", ""),
                }
            return {
                "mode": result.get("mode", "live_validation"),
                "is_consistent": bool(parsed.get("is_consistent")),
                "detected_stance": str(parsed.get("detected_stance", "")).strip(),
                "detected_reason": str(parsed.get("detected_reason", "")).strip(),
                "why": str(parsed.get("why", "")).strip(),
            }

        return self._run_with_optional_trace(
            name="ai.validate_consumer_quote",
            run_type="llm",
            operation=execute,
            trace_inputs={
                "expected_stance": expected_stance,
                "expected_reason_tag": expected_reason_tag,
                "quote_preview": quote[:120],
            },
        )

    def _build_image_content(self, image_path: Path, prompt: str) -> list[dict[str, Any]]:
        mime_type = "image/png"
        if image_path.suffix.lower() in {".jpg", ".jpeg"}:
            mime_type = "image/jpeg"
        image_base64 = base64.b64encode(image_path.read_bytes()).decode("ascii")
        return [
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
            },
        ]

    def _create_vision_completion(self, image_path: Path, prompt: str):
        return self.client.chat.completions.create(
            model=self.config.vision_model,
            messages=[
                {
                    "role": "user",
                    "content": self._build_image_content(image_path, prompt),
                }
            ],
        )

    def _build_extraction_image_parts(self, image_path: Path, temp_dir: Path) -> list[Path]:
        file_size = image_path.stat().st_size
        with Image.open(image_path) as source_image:
            image = source_image.convert("RGB")
            width, height = image.size
            aspect_ratio = height / max(width, 1)

            if aspect_ratio <= 4 and height <= 5000 and file_size <= 4_000_000:
                return [image_path]

            tile_count = min(5, max(2, math.ceil(height / 5000)))
            overlap = 240
            stride = math.ceil(height / tile_count)
            tile_height = min(height, stride + overlap)
            parts: list[Path] = []

            for index in range(tile_count):
                top = index * stride
                if top >= height:
                    break
                bottom = min(height, top + tile_height)
                if index == tile_count - 1:
                    bottom = height
                    top = max(0, bottom - tile_height)

                crop = image.crop((0, top, width, bottom))
                crop = self._resize_for_vision(crop)
                part_path = temp_dir / f"{image_path.stem}_extract_part_{index + 1}.jpg"
                crop.save(part_path, format="JPEG", quality=82, optimize=True)
                parts.append(part_path)

            return parts or [image_path]

    def _resize_for_vision(self, image: Image.Image) -> Image.Image:
        max_width = 1280
        max_height = 2800
        scale = min(max_width / image.width, max_height / image.height, 1.0)
        if scale >= 1.0:
            return image
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _merge_extracted_fields(self, accumulated: Dict[str, Any], current: Dict[str, Any]) -> Dict[str, Any]:
        merged = dict(accumulated)
        list_fields = {"core_claims", "target_channels", "competitors"}
        longer_text_fields = {"detail_copy", "ingredients", "validation_questions"}

        for key, value in current.items():
            if key in list_fields:
                existing = merged.get(key, [])
                if not isinstance(existing, list):
                    existing = []
                for item in value:
                    if item not in existing:
                        existing.append(item)
                merged[key] = existing
                continue

            if key == "price":
                if value:
                    merged[key] = value
                continue

            if key in longer_text_fields:
                if value and len(str(value)) > len(str(merged.get(key, ""))):
                    merged[key] = value
                continue

            if value and not merged.get(key):
                merged[key] = value

        return merged

    def _get_ocr_engine(self):
        if self._ocr_unavailable:
            return None
        if self._ocr_engine is None:
            self._ocr_engine = RapidOCR()
        return self._ocr_engine

    def _extract_ocr_text(self, image_path: Path) -> str:
        remote_text = self._extract_ocr_text_via_remote(image_path)
        if remote_text:
            return remote_text

        ocr_engine = self._get_ocr_engine()
        if ocr_engine is None:
            return ""

        lines: list[str] = []
        with tempfile.TemporaryDirectory() as temp_dir_raw:
            image_parts = self._build_extraction_image_parts(image_path, Path(temp_dir_raw))
            for image_part in image_parts:
                result, _ = ocr_engine(image_part)
                if not result:
                    continue
                for item in result:
                    if len(item) < 2:
                        continue
                    text = str(item[1]).strip()
                    if text:
                        lines.append(text)

        deduped: list[str] = []
        seen: set[str] = set()
        for line in lines:
            if line in seen:
                continue
            seen.add(line)
            deduped.append(line)
        return "\n".join(deduped)

    def _extract_ocr_text_via_remote(self, image_path: Path) -> str:
        def execute() -> str:
            if not self.config.ocr_base_url or not self.config.ocr_model:
                return ""

            ocr_lines: list[str] = []
            endpoint = f"{self.config.ocr_base_url.rstrip('/')}/chat/completions"

            with tempfile.TemporaryDirectory() as temp_dir_raw:
                image_parts = self._build_extraction_image_parts(image_path, Path(temp_dir_raw))
                for image_part in image_parts:
                    image_base64 = base64.b64encode(image_part.read_bytes()).decode("ascii")
                    payload = {
                        "model": self.config.ocr_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "Read all visible text and return plain text only."},
                                    {
                                        "type": "image_url",
                                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                                    },
                                ],
                            }
                        ],
                    }
                    try:
                        response = requests.post(endpoint, json=payload, timeout=self.config.ocr_timeout_seconds)
                        response.raise_for_status()
                        content = response.json()["choices"][0]["message"]["content"]
                        if content:
                            ocr_lines.extend([line.strip() for line in str(content).splitlines() if line.strip()])
                    except Exception:
                        return ""

            deduped: list[str] = []
            seen: set[str] = set()
            for line in ocr_lines:
                if line in seen:
                    continue
                seen.add(line)
                deduped.append(line)
            return "\n".join(deduped)

        return self._run_with_optional_trace(
            name="ai.remote_ocr",
            run_type="tool",
            operation=execute,
            trace_inputs={
                "image_path": str(image_path),
                "ocr_model": self.config.ocr_model,
            },
        )

    def _structure_fields_from_ocr_text(self, ocr_text: str) -> Dict[str, Any]:
        if not ocr_text.strip():
            return {}

        prompt = (
            "You are extracting structured product testing input from OCR text taken from a Chinese product image or detail page. "
            "Return JSON only with this schema: "
            "{\"concept_name\":\"\",\"brand\":\"\",\"category\":\"\",\"core_claims\":[],\"price\":\"\","
            "\"packaging_summary\":\"\",\"target_channels\":[],\"target_audience\":\"\",\"competitors\":[],"
            "\"slogan\":\"\",\"ingredients\":\"\",\"detail_copy\":\"\",\"validation_questions\":\"\"}. "
            "Rules: use only what is supported by the OCR text; do not invent unseen details; "
            "price must stay empty if no explicit selling price or price range is visible; "
            "core_claims should be the strongest 3-8 visible benefits or proof points; "
            "packaging_summary can summarize the apparent product form and the main on-pack communication, even if color detail is unavailable."
            "\n\nOCR text:\n"
            f"{ocr_text[:12000]}"
        )
        structured = self.generate_text(
            prompt=prompt,
            system_prompt="Extract product fields from OCR text and answer with strict JSON only.",
        )
        return _normalize_extracted_fields(_extract_json_object(structured.get("text", "")))

    def _heuristic_fields_from_ocr_text(self, ocr_text: str) -> Dict[str, Any]:
        fields: Dict[str, Any] = {}
        replacements = {
            "防蜓": "防蛀",
            "抗糖酸防": "抗糖酸防蛀",
            "Sakcy Kids": "Saky Kids",
            "健*白": "健白",
            "*": "",
            "蛀蛀": "蛀",
        }
        normalized_text = ocr_text
        for old, new in replacements.items():
            normalized_text = normalized_text.replace(old, new)
        lines = [line.strip() for line in normalized_text.splitlines() if line.strip()]

        product_name_match = re.search(r"产品名称[:：]\s*([^\n]+)", normalized_text)
        if product_name_match:
            fields["concept_name"] = product_name_match.group(1).strip()

        brand_candidates = [
            line
            for line in lines
            if ("舒客" in line or "品牌" in line)
            and "牙膏" not in line
            and "产品名称" not in line
            and len(line) <= 8
        ]
        if brand_candidates:
            fields["brand"] = brand_candidates[0].replace("品牌", "").replace("：", "").replace(":", "").strip()
        elif fields.get("concept_name", "").startswith("舒客宝贝"):
            fields["brand"] = "舒客宝贝"

        category_priority = ("儿童牙膏", "儿童口腔护理", "口腔护理", "牙膏")
        category_candidates = []
        for keyword in category_priority:
            category_candidates = [line for line in lines if keyword == line or line.endswith(keyword)]
            if category_candidates:
                break
        if category_candidates:
            for candidate in category_candidates:
                if candidate in category_priority:
                    fields["category"] = candidate
                    break
            if not fields.get("category"):
                candidate = category_candidates[0]
                fields["category"] = "儿童牙膏" if "儿童牙膏" in candidate else candidate

        claim_keywords = ("防蛀", "抗糖", "净白", "长效", "安全", "测试", "变色", "刷牙", "防护", "清洁")
        claims: list[str] = []
        for line in lines:
            if line in {fields.get("concept_name"), fields.get("brand"), fields.get("category"), "商品详情", "商品介绍"}:
                continue
            if len(line) < 4 or len(line) > 24:
                continue
            if any(keyword in line for keyword in claim_keywords):
                if line not in claims:
                    claims.append(line)
            if len(claims) >= 8:
                break
        if claims:
            fields["core_claims"] = claims

        price_match = re.search(r"(?:¥|￥|售价[:：]?|到手价[:：]?|价格[:：]?)\s*(\d+(?:\.\d+)?)", normalized_text)
        if price_match:
            fields["price"] = f"{price_match.group(1)}元"

        audience_match = re.search(r"(?:龄段[:：]?)\s*([0-9\-~至]+岁)", normalized_text)
        if audience_match:
            fields["target_audience"] = audience_match.group(1)
        elif any("2-12岁" in line for line in lines):
            fields["target_audience"] = "2-12岁儿童"

        slogan_candidates = [
            line
            for line in lines
            if len(line) <= 18 and any(keyword in line for keyword in ("防蛀", "小白牙", "净齿", "刷牙"))
        ]
        if slogan_candidates:
            fields["slogan"] = slogan_candidates[0]

        if fields.get("concept_name") or fields.get("core_claims"):
            summary_parts = []
            if fields.get("concept_name"):
                summary_parts.append(f"图片展示的是{fields['concept_name']}相关详情页。")
            if fields.get("core_claims"):
                summary_parts.append(f"主打信息包括：{'；'.join(fields['core_claims'][:4])}。")
            if fields.get("target_audience"):
                summary_parts.append(f"适用人群指向{fields['target_audience']}。")
            fields["packaging_summary"] = "".join(summary_parts)

        if "产品信息" in normalized_text:
            product_info_index = normalized_text.index("产品信息")
            fields["detail_copy"] = normalized_text[product_info_index : product_info_index + 500]

        ingredients_match = re.search(
            r"成分[:：]\s*(.+?)(?:其他微量成分[:：]|功效成分[:：]|使用方法[:：]|注意事项[:：]|$)",
            normalized_text,
            flags=re.S,
        )
        if ingredients_match:
            fields["ingredients"] = re.sub(r"\s+", " ", ingredients_match.group(1)).strip()

        return _normalize_extracted_fields(fields)

    def analyze_image(self, image_path: Path, prompt: str) -> Dict[str, Any]:
        def execute() -> Dict[str, Any]:
            if not self.is_configured or not self.client:
                return {
                    "mode": "fallback_vision",
                    "text": "Fallback visual summary: API configuration is missing, so image analysis used local defaults.",
                    "structured_signals": {
                        "clarity": "unknown",
                        "child_appeal": "unknown",
                        "safety_signal": "unknown",
                        "premium_feel": "unknown",
                    },
                }

            if not self.config.vision_model:
                return {
                    "mode": "fallback_vision",
                    "text": "Fallback visual summary: vision model is disabled, so image analysis used local defaults.",
                    "structured_signals": {
                        "clarity": "unknown",
                        "child_appeal": "unknown",
                        "safety_signal": "unknown",
                        "premium_feel": "unknown",
                    },
                }

            try:
                response = self._create_vision_completion(image_path, prompt)
                text = response.choices[0].message.content or ""
                return {
                    "mode": "live_vision",
                    "model": self.config.vision_model,
                    "text": text,
                    "structured_signals": {
                        "clarity": "model_generated",
                        "child_appeal": "model_generated",
                        "safety_signal": "model_generated",
                        "premium_feel": "model_generated",
                    },
                }
            except Exception as exc:  # pragma: no cover - exercised through tests
                return {
                    "mode": "fallback_vision",
                    "text": "Fallback visual summary: remote image analysis failed, so image analysis used local defaults.",
                    "errors": [f"{self.config.vision_model}: {exc}"],
                    "structured_signals": {
                        "clarity": "unknown",
                        "child_appeal": "unknown",
                        "safety_signal": "unknown",
                        "premium_feel": "unknown",
                    },
                }

        return self._run_with_optional_trace(
            name="ai.analyze_image",
            run_type="tool",
            operation=execute,
            trace_inputs={
                "image_path": str(image_path),
                "prompt_preview": prompt[:400],
                "vision_model": self.config.vision_model,
            },
        )

    def extract_product_fields_from_image(self, image_path: Path) -> Dict[str, Any]:
        if not self.is_configured or not self.client:
            return {
                "mode": "fallback_vision_extraction",
                "fields": {},
                "raw_text": "",
            }

        if not self.config.vision_model:
            return {
                "mode": "fallback_vision_extraction",
                "fields": {},
                "raw_text": "",
            }

        prompt = (
            "You are extracting structured product testing input from a single product image, poster, or detail-page screenshot. "
            "Read all visible text and visual cues carefully. "
            "Return JSON only with this schema: "
            "{\"concept_name\":\"\",\"brand\":\"\",\"category\":\"\",\"core_claims\":[],\"price\":\"\","
            "\"packaging_summary\":\"\",\"target_channels\":[],\"target_audience\":\"\",\"competitors\":[],"
            "\"slogan\":\"\",\"ingredients\":\"\",\"detail_copy\":\"\",\"validation_questions\":\"\","
            "\"confidence\":{\"concept_name\":0,\"category\":0,\"core_claims\":0,\"price\":0,\"packaging_summary\":0}}. "
            "Rules: use only information visible in the image; do not invent missing details; "
            "use empty string or empty array when uncertain; "
            "packaging_summary should summarize the pack design, colors, format, and the most prominent on-pack messages in 1-2 sentences; "
            "price should preserve visible price text if any."
        )

        ocr_text = self._extract_ocr_text(image_path)
        if ocr_text:
            ocr_fields = self._structure_fields_from_ocr_text(ocr_text)
            if not ocr_fields:
                ocr_fields = self._heuristic_fields_from_ocr_text(ocr_text)
            if _count_present_core_fields(ocr_fields) >= 3:
                return {
                    "mode": "live_ocr_extraction",
                    "fields": ocr_fields,
                    "raw_text": ocr_text,
                }

        errors: list[str] = []
        raw_text_parts: list[str] = []
        merged_fields: Dict[str, Any] = {}

        try:
            with tempfile.TemporaryDirectory() as temp_dir_raw:
                image_parts = self._build_extraction_image_parts(image_path, Path(temp_dir_raw))
                for image_part in image_parts:
                    try:
                        response = self._create_vision_completion(image_part, prompt)
                        text = response.choices[0].message.content or ""
                        raw_text_parts.append(text)
                        raw_fields = _normalize_extracted_fields(_extract_json_object(text))
                        merged_fields = self._merge_extracted_fields(merged_fields, raw_fields)
                        if _has_core_extracted_fields(merged_fields):
                            break
                    except Exception as exc:  # pragma: no cover - exercised through tests
                        errors.append(f"{image_part.name}: {exc}")

            if merged_fields:
                result = {
                    "mode": "live_vision_extraction",
                    "model": self.config.vision_model,
                    "fields": merged_fields,
                    "raw_text": "\n\n".join(part for part in raw_text_parts if part),
                }
                if errors:
                    result["errors"] = errors
                return result

        except Exception as exc:  # pragma: no cover - exercised through tests
            errors.append(f"{image_path.name}: {exc}")

        if errors:
            return {
                "mode": "fallback_vision_extraction",
                "fields": {},
                "raw_text": "",
                "errors": errors,
            }

        return {
            "mode": "fallback_vision_extraction",
            "fields": {},
            "raw_text": "",
        }
