import uuid
import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from app.tasks.document_tasks import _process_document_async
from app.db.models import Document, DocumentStatus


@pytest.mark.asyncio
async def test_process_document_success():
    doc_id = str(uuid.uuid4())
    fake_document = MagicMock(spec=Document)
    fake_document.status = DocumentStatus.PENDING

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_document
    mock_db.execute.return_value = mock_result

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None

    with patch("app.tasks.document_tasks.AsyncSessionLocal", return_value=mock_session_cm), \
         patch("app.tasks.document_tasks.download_bytes", return_value=b"fake pdf bytes"), \
         patch("app.tasks.document_tasks.document_pipeline") as mock_pipeline, \
         patch("os.remove"):

        mock_pipeline.invoke.return_value = {
            "file_type": "native_pdf",
            "extraction_method": "native",
            "confidence": 1.0,
            "extracted_text": "Sample extracted text",
        }

        await _process_document_async(doc_id, "uploads/fake.pdf")

    assert fake_document.status == DocumentStatus.COMPLETED
    assert fake_document.extracted_text == "Sample extracted text"


@pytest.mark.asyncio
async def test_process_document_not_found_returns_early():
    doc_id = str(uuid.uuid4())

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None

    with patch("app.tasks.document_tasks.AsyncSessionLocal", return_value=mock_session_cm):
        await _process_document_async(doc_id, "uploads/fake.pdf")

    mock_db.commit.assert_not_called()


@pytest.mark.asyncio
async def test_process_document_pipeline_failure_marks_failed():
    doc_id = str(uuid.uuid4())
    fake_document = MagicMock(spec=Document)
    fake_document.status = DocumentStatus.PENDING

    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = fake_document
    mock_db.execute.return_value = mock_result

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__.return_value = mock_db
    mock_session_cm.__aexit__.return_value = None

    with patch("app.tasks.document_tasks.AsyncSessionLocal", return_value=mock_session_cm), \
         patch("app.tasks.document_tasks.download_bytes", side_effect=Exception("S3 unreachable")):

        await _process_document_async(doc_id, "uploads/fake.pdf")

    assert fake_document.status == DocumentStatus.FAILED
    assert "S3 unreachable" in fake_document.error