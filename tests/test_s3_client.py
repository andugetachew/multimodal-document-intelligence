from unittest.mock import patch, MagicMock

from app.services.storage.s3_client import (
    upload_bytes, download_bytes, delete_object, ensure_bucket_exists,
)


@patch("app.services.storage.s3_client.s3_client")
def test_upload_bytes_calls_put_object(mock_client):
    key = upload_bytes("test-key.pdf", b"file content")

    mock_client.put_object.assert_called_once()
    assert key == "test-key.pdf"


@patch("app.services.storage.s3_client.s3_client")
def test_download_bytes_returns_content(mock_client):
    mock_body = MagicMock()
    mock_body.read.return_value = b"downloaded content"
    mock_client.get_object.return_value = {"Body": mock_body}

    result = download_bytes("test-key.pdf")

    assert result == b"downloaded content"


@patch("app.services.storage.s3_client.s3_client")
def test_delete_object_calls_delete(mock_client):
    delete_object("test-key.pdf")

    mock_client.delete_object.assert_called_once()


@patch("app.services.storage.s3_client.s3_client")
def test_ensure_bucket_creates_when_missing(mock_client):
    mock_client.list_buckets.return_value = {"Buckets": []}

    ensure_bucket_exists()

    mock_client.create_bucket.assert_called_once()


@patch("app.services.storage.s3_client.s3_client")
def test_ensure_bucket_skips_when_exists(mock_client):
    from app.core.config import get_settings
    bucket_name = get_settings().S3_BUCKET_NAME
    mock_client.list_buckets.return_value = {"Buckets": [{"Name": bucket_name}]}

    ensure_bucket_exists()

    mock_client.create_bucket.assert_not_called()