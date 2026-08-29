from __future__ import annotations

from urllib.parse import quote

import boto3

from core.config import settings


class R2StorageConfigurationError(RuntimeError):
    pass


class R2Storage:
    def __init__(
        self,
        *,
        bucket: str | None = None,
        endpoint: str | None = None,
        region: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        public_base_url: str | None = None,
        client=None,
    ) -> None:
        self.bucket = bucket or settings.r2_bucket
        self.endpoint = (endpoint or settings.resolved_r2_endpoint or "").rstrip("/")
        self.region = region or settings.r2_region
        self.public_base_url = (public_base_url or settings.r2_public_base_url or "").rstrip("/")

        if client is None:
            missing = [
                name
                for name, value in (
                    ("R2_ACCESS_KEY_ID", access_key_id or settings.r2_access_key_id),
                    ("R2_SECRET_ACCESS_KEY", secret_access_key or settings.r2_secret_access_key),
                    ("R2_ENDPOINT", self.endpoint),
                    ("R2_BUCKET", self.bucket),
                )
                if not value
            ]
            if missing:
                raise R2StorageConfigurationError(
                    f"R2 storage is not configured. Missing required settings: {', '.join(missing)}"
                )
            client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                region_name=self.region,
                aws_access_key_id=access_key_id or settings.r2_access_key_id,
                aws_secret_access_key=secret_access_key or settings.r2_secret_access_key,
            )
        self.client = client

    def upload_bytes(self, key: str, content: bytes, content_type: str, *, cache_control: str | None = None) -> str:
        extra = {"CacheControl": cache_control} if cache_control else {}
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
            **extra,
        )
        return self.build_public_url(key)

    def upload_file(self, local_path: str, key: str, content_type: str) -> str:
        with open(local_path, "rb") as file_obj:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=file_obj,
                ContentType=content_type,
            )
        return self.build_public_url(key)

    def download_bytes(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        return response["Body"].read()

    def delete_object(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def copy_object(self, source_key: str, target_key: str, *, cache_control: str | None = None) -> str:
        extra = {"CacheControl": cache_control, "MetadataDirective": "REPLACE"} if cache_control else {}
        self.client.copy_object(Bucket=self.bucket, Key=target_key, CopySource={"Bucket": self.bucket, "Key": source_key}, ContentType="text/html; charset=utf-8", **extra)
        return self.build_public_url(target_key)

    def build_public_url(self, key: str) -> str:
        encoded_key = quote(key, safe="/")
        if self.public_base_url:
            return f"{self.public_base_url}/{encoded_key}"
        if self.endpoint:
            return f"{self.endpoint}/{self.bucket}/{encoded_key}"
        raise R2StorageConfigurationError("Cannot build R2 public URL without an endpoint or public base URL.")

    def head_object(self, key: str) -> dict:
        return self.client.head_object(Bucket=self.bucket, Key=key)

    def list_objects(self, *, prefix: str, continuation_token: str | None = None, max_keys: int = 1000) -> dict:
        extra = {"ContinuationToken": continuation_token} if continuation_token else {}
        return self.client.list_objects_v2(Bucket=self.bucket, Prefix=prefix, MaxKeys=max_keys, **extra)
