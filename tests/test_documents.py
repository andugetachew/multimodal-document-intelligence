import io
from unittest.mock import patch, MagicMock

import pytest


@pytest.mark.asyncio
async def test_upload_document_success(client):
    fake_pdf_bytes = b"%PDF-1.4 fake content for testing"

    with patch("app.api.documents.upload_bytes") as mock_upload, \
         patch("app.api.documents.process_document") as mock_task:

        mock_upload.return_value = "uploads/fake-key.pdf"
        mock_task.delay = MagicMock()

        response = await client.post(
            "/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(fake_pdf_bytes), "application/pdf")},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["original_filename"] == "test.pdf"
    assert data["status"] == "pending"
    assert data["extracted_text"] is None

    mock_upload.assert_called_once()
    mock_task.delay.assert_called_once()


@pytest.mark.asyncio
async def test_upload_document_too_large(client):
    oversized_bytes = b"x" * (2 * 1024 * 1024)

    with patch("app.api.documents.settings.MAX_UPLOAD_SIZE_MB", 0), \
         patch("app.api.documents.upload_bytes"), \
         patch("app.api.documents.process_document"):

        response = await client.post(
            "/documents/upload",
            files={"file": ("big.pdf", io.BytesIO(oversized_bytes), "application/pdf")},
        )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_document_storage_failure_returns_502(client):
    fake_bytes = b"some file content"

    with patch("app.api.documents.upload_bytes") as mock_upload, \
         patch("app.api.documents.process_document"):

        mock_upload.side_effect = Exception("MinIO connection refused")

        response = await client.post(
            "/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(fake_bytes), "application/pdf")},
        )

    assert response.status_code == 502
    assert "Storage upload failed" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_document_not_found(client):
    import uuid
    fake_id = uuid.uuid4()

    response = await client.get(f"/documents/{fake_id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document not found"


@pytest.mark.asyncio
async def test_get_document_success(client):
    fake_pdf_bytes = b"%PDF-1.4 fake content"

    with patch("app.api.documents.upload_bytes") as mock_upload, \
         patch("app.api.documents.process_document") as mock_task:

        mock_upload.return_value = "uploads/fake-key.pdf"
        mock_task.delay = MagicMock()

        upload_response = await client.post(
            "/documents/upload",
            files={"file": ("test.pdf", io.BytesIO(fake_pdf_bytes), "application/pdf")},
        )

    document_id = upload_response.json()["id"]

    get_response = await client.get(f"/documents/{document_id}")

    assert get_response.status_code == 200
    assert get_response.json()["id"] == document_id
    assert get_response.json()["status"] == "pending"

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