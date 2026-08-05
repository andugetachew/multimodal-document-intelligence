import os
import tempfile
import asyncio

from app.core.celery_app import celery_app
from app.services.storage.s3_client import download_bytes, upload_bytes
from app.graph.pipeline import document_pipeline
from app.db.session import AsyncSessionLocal
from app.db.models import Document, DocumentStatus

import uuid
from sqlalchemy import select


@celery_app.task(name="process_document")
def process_document(document_id: str, storage_key: str):
    asyncio.run(_process_document_async(document_id, storage_key))


async def _process_document_async(document_id: str, storage_key: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Document).where(Document.id == uuid.UUID(document_id)))
        document = result.scalar_one_or_none()
        if not document:
            return

        document.status = DocumentStatus.PROCESSING
        await db.commit()

        try:
            file_bytes = download_bytes(storage_key)
            ext = os.path.splitext(storage_key)[1]

            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                tmp.write(file_bytes)
                tmp_path = tmp.name

            try:
                pipeline_result = document_pipeline.invoke({"file_path": tmp_path})
            finally:
                os.remove(tmp_path)

            document.file_type = pipeline_result.get("file_type")
            document.extraction_method = pipeline_result.get("extraction_method")
            document.confidence = pipeline_result.get("confidence")
            document.extracted_text = pipeline_result.get("extracted_text")
            document.status = DocumentStatus.COMPLETED

        except Exception as e:
            document.status = DocumentStatus.FAILED
            document.error = str(e)

        await db.commit()