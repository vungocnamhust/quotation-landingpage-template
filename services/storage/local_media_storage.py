from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote


class LocalMediaStorage:
    def __init__(
        self,
        *,
        root_dir: str = "published",
        public_base_path: str = "/published",
        bucket: str = "local-media",
    ) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.public_base_path = public_base_path.rstrip("/") or "/published"
        self.bucket = bucket
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_path(self, key: str) -> Path:
        safe_key = (key or "").lstrip("/")
        target = (self.root_dir / safe_key).resolve()
        if target != self.root_dir and self.root_dir not in target.parents:
            raise ValueError("Storage key resolves outside the local media root.")
        return target

    def upload_bytes(self, key: str, content: bytes, content_type: str) -> str:
        target = self._resolve_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return self.build_public_url(key)

    def upload_file(self, local_path: str, key: str, content_type: str) -> str:
        target = self._resolve_path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "rb") as file_obj:
            target.write_bytes(file_obj.read())
        return self.build_public_url(key)

    def download_bytes(self, key: str) -> bytes:
        return self._resolve_path(key).read_bytes()

    def delete_object(self, key: str) -> None:
        target = self._resolve_path(key)
        try:
            target.unlink()
        except FileNotFoundError:
            return

    def build_public_url(self, key: str) -> str:
        encoded_key = quote((key or "").lstrip("/"), safe="/")
        return f"{self.public_base_path}/{encoded_key}"

    def head_object(self, key: str) -> dict:
        target = self._resolve_path(key)
        stat = target.stat()
        return {
            "ContentLength": stat.st_size,
            "LastModified": stat.st_mtime,
            "Key": key,
        }
