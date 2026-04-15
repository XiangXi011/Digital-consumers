"""File upload API for the web intake flow."""

import structlog
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.auth.dependencies import get_current_user
from backend.paths import WEB_UPLOADS_DIR

logger = structlog.get_logger(__name__)

router = APIRouter()

WEB_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".pdf", ".doc", ".docx"}
MAX_FILE_SIZE = 10 * 1024 * 1024


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    path: str
    relative_path: str
    size: int


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not allowed. Supported: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"File too large. Max: {MAX_FILE_SIZE // 1024 // 1024}MB")

    file_id = uuid.uuid4().hex
    unique_name = f"{file_id[:8]}_{file.filename}"
    save_path = WEB_UPLOADS_DIR / unique_name
    save_path.write_bytes(content)
    logger.info("File uploaded: %s (%d bytes)", unique_name, len(content))
    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        path=str(save_path),
        relative_path=f"web_uploads/{unique_name}",
        size=len(content),
    )


@router.get("/upload/{filename}/preview")
async def get_thumbnail(filename: str, user=Depends(get_current_user)):
    """Generate and return a thumbnail for an uploaded image."""
    from fastapi.responses import FileResponse

    from backend.infra.media_processor import generate_thumbnail, is_image_file

    source_path = WEB_UPLOADS_DIR / filename
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    if not is_image_file(source_path):
        raise HTTPException(status_code=400, detail="File is not an image")

    thumb_dir = WEB_UPLOADS_DIR / "thumbnails"
    thumb_path = generate_thumbnail(source_path, thumb_dir)
    if thumb_path is None:
        raise HTTPException(status_code=500, detail="Thumbnail generation failed")

    return FileResponse(thumb_path, media_type="image/jpeg")
