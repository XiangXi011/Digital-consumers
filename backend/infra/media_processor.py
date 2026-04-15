"""Unified media processing: image validation, thumbnail generation, vision analysis."""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


def is_image_file(path: Path | str) -> bool:
    """Check if a file path refers to a supported image format."""
    return Path(path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def validate_image(path: Path) -> Dict[str, Any]:
    """Validate an image file and return metadata.

    Returns dict with: valid, width, height, format, size_bytes, error
    """
    try:
        from PIL import Image

        if not path.exists():
            return {"valid": False, "error": f"File not found: {path}"}

        size = path.stat().st_size
        if size > MAX_IMAGE_SIZE_BYTES:
            return {"valid": False, "error": f"Image too large: {size} bytes (max {MAX_IMAGE_SIZE_BYTES})"}

        with Image.open(path) as img:
            return {
                "valid": True,
                "width": img.width,
                "height": img.height,
                "format": img.format,
                "size_bytes": size,
            }
    except Exception as exc:
        return {"valid": False, "error": str(exc)}


def generate_thumbnail(
    source_path: Path,
    output_dir: Path,
    max_size: int = 256,
) -> Optional[str]:
    """Generate a thumbnail for an image file.

    Returns the relative path to the thumbnail, or None on failure.
    """
    try:
        from PIL import Image

        if not is_image_file(source_path):
            return None

        output_dir.mkdir(parents=True, exist_ok=True)
        thumb_name = f"thumb_{source_path.stem}.jpg"
        thumb_path = output_dir / thumb_name

        with Image.open(source_path) as img:
            img.thumbnail((max_size, max_size), Image.LANCZOS)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(thumb_path, "JPEG", quality=85)

        return str(thumb_path)
    except Exception as exc:
        logger.warning("Thumbnail generation failed for %s: %s", source_path, exc)
        return None


def analyze_image_with_vision(
    image_path: Path,
    prompt: str,
    ai_client: Any,
) -> Dict[str, Any]:
    """Analyze an image using the AI client's vision capabilities.

    Returns dict with: description, raw_response, model
    """
    try:
        result = ai_client.analyze_image(image_path, prompt)
        return {
            "status": "success",
            "description": result.get("text", ""),
            "model": result.get("model", ""),
            "raw_response": result,
        }
    except Exception as exc:
        logger.warning("Vision analysis failed for %s: %s", image_path, exc)
        return {"status": "failed", "error": str(exc)}
