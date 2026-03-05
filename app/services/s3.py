from __future__ import annotations

import uuid

import boto3
from botocore.client import BaseClient
from botocore.config import Config as BotoConfig

from app.core.config import settings


def get_s3_client() -> BaseClient:
    return boto3.client(
        "s3",
        region_name=settings.S3_REGION,
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
        config=BotoConfig(
            s3={"addressing_style": settings.s3_addressing_style}
        ),
    )


def build_s3_key(*, tenant_id: str, attachment_id: uuid.UUID, filename: str) -> str:
    safe_name = filename.replace("\\", "_").replace("/", "_")
    return f"{tenant_id}/attachments/{attachment_id}/{safe_name}"


def presign_upload(*, key: str, content_type: str) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.PRESIGNED_URL_EXPIRES_SECONDS,
    )


def presign_download(*, key: str) -> str:
    client = get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.S3_BUCKET, "Key": key},
        ExpiresIn=settings.PRESIGNED_URL_EXPIRES_SECONDS,
    )
