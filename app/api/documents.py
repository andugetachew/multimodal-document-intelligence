import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Document, DocumentStatus
from app.schemas.document import DocumentResponse
from app.core.config import get_settings
from app.services.storage.s3_client import upload_bytes
from app.tasks.document_tasks import process_document
from fastapi import Query
from app.services.storage.s3_client import delete_object

router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    file_id = uuid.uuid4()
    ext = os.path.splitext(file.filename)[1]
    storage_key = f"uploads/{file_id}{ext}"

    contents = b""
    size = 0
    while chunk := await file.read(1024 * 1024):
        size += len(chunk)
        if size > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
            raise HTTPException(413, "File too large")
        contents += chunk

    try:
        upload_bytes(storage_key, contents)
    except Exception as e:
        raise HTTPException(502, f"Storage upload failed: {e}")

    document = Document(
        id=file_id,
        original_filename=file.filename,
        storage_key=storage_key,
        status=DocumentStatus.PENDING,
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    process_document.delay(str(document.id), storage_key)

    return document

@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    result = await db.execute(
        select(Document).order_by(Document.created_at.desc()).limit(limit).offset(offset)
    )
    return result.scalars().all()


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(404, "Document not found")

    try:
        delete_object(document.storage_key)
    except Exception:
        pass

    await db.delete(document)
    await db.commit()
    
@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == document_id))
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(404, "Document not found")

    return document