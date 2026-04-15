"""Image generation API proxy."""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.auth.dependencies import get_current_user
from backend.paths import OUTPUTS_DIR

router = APIRouter()

AVATAR_CACHE_DIR = OUTPUTS_DIR / "persona_avatars"
AVATAR_CACHE_FILE = AVATAR_CACHE_DIR / "avatar_cache.json"


class ImageGenerationRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    model: Optional[str] = None
    size: str = "2K"
    response_format: str = "url"
    watermark: bool = True
    cache_key: Optional[str] = None
    use_cache: bool = True


class ImageItem(BaseModel):
    url: Optional[str] = None
    b64_json: Optional[str] = None
    revised_prompt: Optional[str] = None


class ImageGenerationResponse(BaseModel):
    created: Optional[int] = None
    model: Optional[str] = None
    data: List[ImageItem] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)
    cached: bool = False


def _load_avatar_cache() -> Dict[str, Any]:
    if not AVATAR_CACHE_FILE.exists():
        return {"items": {}}
    try:
        data = json.loads(AVATAR_CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"items": {}}
    items = data.get("items")
    if not isinstance(items, dict):
        return {"items": {}}
    return {"items": items}


def _save_avatar_cache(store: Dict[str, Any]) -> None:
    AVATAR_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    AVATAR_CACHE_FILE.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def _make_cache_key(payload: Dict[str, Any], explicit_key: Optional[str]) -> str:
    if explicit_key and str(explicit_key).strip():
        return str(explicit_key).strip()
    content = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


@router.post("/images/generations", response_model=ImageGenerationResponse)
def generate_image(request: ImageGenerationRequest, user=Depends(get_current_user)):
    api_key = os.getenv("IMAGE_API_KEY", "").strip()
    base_url = os.getenv("IMAGE_API_BASE_URL", "https://www.moyu.info/v1").rstrip("/")
    default_model = os.getenv("IMAGE_MODEL", "doubao-seedream-5-0-260128").strip()

    if not api_key:
        raise HTTPException(status_code=400, detail="IMAGE_API_KEY 未配置")

    payload = {
        "model": request.model or default_model,
        "prompt": request.prompt,
        "size": request.size,
        "response_format": request.response_format,
        "watermark": request.watermark,
    }

    cache_key = _make_cache_key(payload, request.cache_key)
    if request.use_cache:
        store = _load_avatar_cache()
        item = store.get("items", {}).get(cache_key)
        if isinstance(item, dict):
            cached_url = str(item.get("url", "") or "").strip()
            if cached_url:
                return ImageGenerationResponse(
                    model=payload["model"],
                    data=[ImageItem(url=cached_url)],
                    raw={"cache_key": cache_key, "cache_hit": True},
                    cached=True,
                )

    try:
        resp = requests.post(
            f"{base_url}/images/generations",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=120,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生图服务调用失败: {exc}")

    if resp.status_code >= 400:
        detail = resp.text[:1000]
        raise HTTPException(status_code=resp.status_code, detail=f"生图服务返回错误: {detail}")

    try:
        data = resp.json()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"生图服务返回非 JSON: {exc}")

    items = data.get("data", [])
    if not isinstance(items, list):
        items = []

    normalized_items = []
    first_url = ""
    for item in items:
        if isinstance(item, dict):
            url = item.get("url")
            if not first_url and isinstance(url, str):
                first_url = url.strip()
            normalized_items.append(
                ImageItem(
                    url=url,
                    b64_json=item.get("b64_json"),
                    revised_prompt=item.get("revised_prompt"),
                )
            )

    if request.use_cache and first_url:
        store = _load_avatar_cache()
        store.setdefault("items", {})[cache_key] = {
            "url": first_url,
            "model": payload["model"],
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        _save_avatar_cache(store)

    return ImageGenerationResponse(
        created=data.get("created"),
        model=payload["model"],
        data=normalized_items,
        raw={**data, "cache_key": cache_key, "cache_hit": False},
        cached=False,
    )
