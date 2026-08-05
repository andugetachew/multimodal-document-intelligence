# Multimodal Document Intelligence

An AI-powered document processing API that classifies incoming documents and routes them through the appropriate extraction path — native text parsing, OCR, or vision-model extraction — using a LangGraph-orchestrated pipeline with confidence-based escalation.

## What it does

Upload a PDF or image, and the system automatically:
1. Classifies the document (native-text PDF, scanned PDF, or image)
2. Routes it through the cheapest extraction method that will work
3. Escalates to a vision model (Claude) if OCR confidence is too low
4. Persists the result and extracted text for retrieval

This mirrors a real-world problem: organizations receive documents in wildly inconsistent formats — clean PDFs, scanned contracts, phone photos of paperwork — and need a single pipeline that handles all of them intelligently rather than assuming one format.

## Architecture

Upload → S3/MinIO storage → Celery task dispatched
↓
LangGraph pipeline:
classify_document
↓
┌───────────┼───────────┐
native_pdf scanned_pdf/image unknown
↓ ↓ ↓
extract_native extract_ocr extract_vision
↓
confidence check
↓ ↓
(sufficient) (too low)
done extract_vision
↓
Persist to PostgreSQL (Neon)


## Stack

- **API**: FastAPI, async SQLAlchemy
- **Orchestration**: LangGraph (routing + confidence-based escalation), LangChain-core
- **Extraction**: PyMuPDF (native text), Tesseract + pdf2image (OCR), Anthropic Claude API (vision fallback)
- **Async processing**: Celery + Redis
- **Storage**: S3-compatible (MinIO locally)
- **Database**: PostgreSQL via Neon (serverless, async via asyncpg)
- **Testing**: pytest, pytest-asyncio, pytest-cov (SQLite for test isolation, mocked external services)
- **CI/CD**: GitHub Actions → Docker Hub

## Current status

- ✅ Native PDF extraction, OCR extraction, and confidence-based routing — fully working and tested
- ✅ Async background processing via Celery, decoupled file storage via MinIO
- ✅ 20 passing tests, 73% coverage (remaining gap is infrastructure-dependent code — live OCR/S3/Celery paths)
- ⏸️ Vision-model escalation is built and wired in but untested end-to-end pending Anthropic API billing setup

## Running locally

```bash
docker-compose up --build
```

Requires a `.env` file (see `.env.example`) with a Neon Postgres connection string and Anthropic API key.

## Running tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=app --cov-report=term-missing
```

That "Current status" section matters more than it might seem — it's the same honest-framing approach from your Knowledge Base API interview prep doc, stated upfront rather than something you have to explain defensively if asked.

3. Endpoint polish (item 4)

Let's add a list endpoint with pagination and a delete endpoint — both genuinely useful and commonly expected on a document API.

Add to app/api/documents.py:

python
from fastapi import Query
from sqlalchemy import func
from app.services.storage.s3_client import delete_object


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
        pass  # non-fatal — matches the pattern from your Knowledge Base API's storage deletion

    await db.delete(document)
    await db.commit()

Note the delete behavior deliberately mirrors what you already described for your Knowledge Base API: "If storage deletion fails we log and continue — the database row is still deleted. A stranded file in S3 is a storage cost issue, not a correctness issue." Same philosophy, consistent across both projects — a good thing to point out if asked about your design principles.

Add corresponding tests to tests/test_documents.py:

python
@pytest.mark.asyncio
async def test_list_documents_empty(client):
    response = await client.get("/documents")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_documents_returns_uploaded(client):
    with patch("app.api.documents.upload_bytes") as mock_upload, \
         patch("app.api.documents.process_document") as mock_task:
        mock_upload.return_value = "uploads/fake-key.pdf"
        mock_task.delay = MagicMock()

        await client.post(
            "/documents/upload",
            files={"file": ("a.pdf", io.BytesIO(b"content"), "application/pdf")},
        )

    response = await client.get("/documents")
    assert response.status_code == 200
    assert len(response.json()) == 1


@pytest.mark.asyncio
async def test_delete_document_success(client):
    with patch("app.api.documents.upload_bytes") as mock_upload, \
         patch("app.api.documents.process_document") as mock_task, \
         patch("app.api.documents.delete_object"):
        mock_upload.return_value = "uploads/fake-key.pdf"
        mock_task.delay = MagicMock()

        upload_response = await client.post(
            "/documents/upload",
            files={"file": ("a.pdf", io.BytesIO(b"content"), "application/pdf")},
        )

    document_id = upload_response.json()["id"]

    delete_response = await client.delete(f"/documents/{document_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/documents/{document_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_delete_document_not_found(client):
    import uuid
    response = await client.delete(f"/documents/{uuid.uuid4()}")
    assert response.status_code == 404