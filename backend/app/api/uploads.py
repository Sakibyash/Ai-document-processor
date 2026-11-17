import os
import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.serializers import document_to_dict
from app.config import settings
from app.database import get_db
from app.models import Document, ProcessingHistory
from app.processors.base import detect_kind
from app.workers.pipeline import process_document

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

ALLOWED_EXTS = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp",
    ".xlsx", ".xls", ".csv", ".txt", ".md", ".docx",
}


@router.post("")
async def upload_document(file: UploadFile, db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTS))}")

    max_bytes = settings.max_upload_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")
    if not content:
        raise HTTPException(400, "Empty file")

    doc_id = str(uuid.uuid4())
    storage_dir = os.path.join(settings.storage_dir, doc_id)
    os.makedirs(storage_dir, exist_ok=True)
    storage_path = os.path.join(storage_dir, file.filename or "upload" + ext)
    with open(storage_path, "wb") as f:
        f.write(content)

    try:
        detect_kind(file.filename or "")
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    doc = Document(
        id=doc_id,
        filename=file.filename or "unnamed",
        content_type=file.content_type or "",
        file_size=len(content),
        storage_path=storage_path,
    )
    db.add(doc)
    db.add(ProcessingHistory(document_id=doc.id, stage="upload", status="completed"))
    db.commit()
    db.refresh(doc)

    # Queue background processing (falls back to eager inline run if broker is down)
    try:
        process_document.delay(doc.id)
    except Exception:
        process_document.apply(args=[doc.id])

    return document_to_dict(doc)
