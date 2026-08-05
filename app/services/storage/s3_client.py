import boto3
from botocore.client import Config

from app.core.config import get_settings

settings = get_settings()

s3_client = boto3.client(
    "s3",
    endpoint_url=settings.S3_ENDPOINT_URL,
    aws_access_key_id=settings.S3_ACCESS_KEY,
    aws_secret_access_key=settings.S3_SECRET_KEY,
    region_name=settings.S3_REGION,
    config=Config(signature_version="s3v4"),
)


def ensure_bucket_exists():
    existing = [b["Name"] for b in s3_client.list_buckets().get("Buckets", [])]
    if settings.S3_BUCKET_NAME not in existing:
        s3_client.create_bucket(Bucket=settings.S3_BUCKET_NAME)


def upload_bytes(key: str, data: bytes) -> str:
    s3_client.put_object(Bucket=settings.S3_BUCKET_NAME, Key=key, Body=data)
    return key


def download_bytes(key: str) -> bytes:
    obj = s3_client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    return obj["Body"].read()


def delete_object(key: str) -> None:
    s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)