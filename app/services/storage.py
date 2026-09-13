import asyncio
from functools import cached_property
from typing import BinaryIO

import boto3
from botocore.config import Config

from app.core.config import settings


class R2StorageService:
    @cached_property
    def client(self):  # type: ignore[no-untyped-def]
        if not all(
            [settings.r2_account_id, settings.r2_access_key_id, settings.r2_secret_access_key]
        ):
            raise RuntimeError("Cloudflare R2 credentials are not configured")
        return boto3.client(
            "s3",
            endpoint_url=f"https://{settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=settings.r2_access_key_id,
            aws_secret_access_key=settings.r2_secret_access_key,
            region_name="auto",
            config=Config(signature_version="s3v4"),
        )

    async def upload(self, body: BinaryIO, object_key: str, content_type: str) -> None:
        await asyncio.to_thread(
            self.client.upload_fileobj,
            body,
            settings.r2_bucket_name,
            object_key,
            ExtraArgs={"ContentType": content_type},
        )

    async def delete(self, object_key: str) -> None:
        await asyncio.to_thread(
            self.client.delete_object, Bucket=settings.r2_bucket_name, Key=object_key
        )

    async def get_url(self, object_key: str) -> str:
        if settings.r2_public_base_url:
            return f"{settings.r2_public_base_url.rstrip('/')}/{object_key}"
        return await asyncio.to_thread(
            self.client.generate_presigned_url,
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": object_key},
            ExpiresIn=settings.r2_presigned_url_expire_seconds,
        )


storage_service = R2StorageService()
