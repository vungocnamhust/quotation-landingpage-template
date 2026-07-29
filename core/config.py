from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return int(raw_value)


def _normalize_endpoint_url(value: str) -> str:
    raw_value = (value or "").strip()
    if not raw_value:
        return ""

    candidate = raw_value if "://" in raw_value else f"https://{raw_value}"
    parsed = urlsplit(candidate)
    if not parsed.netloc:
        return raw_value.rstrip("/")

    scheme = parsed.scheme or "https"
    return urlunsplit((scheme, parsed.netloc, "", "", "")).rstrip("/")


def _derive_sync_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return database_url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    return database_url


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://quotation:quotation_password@postgres:5432/quotation",
    )
    database_url_sync: str = os.getenv(
        "DATABASE_URL_SYNC",
        _derive_sync_database_url(
            os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://quotation:quotation_password@postgres:5432/quotation",
            )
        ),
    )
    db_echo: bool = _get_bool("DB_ECHO", False)
    db_pool_size: int = _get_int("DB_POOL_SIZE", 10)
    db_max_overflow: int = _get_int("DB_MAX_OVERFLOW", 20)
    db_pool_timeout: int = _get_int("DB_POOL_TIMEOUT", 30)
    db_pool_recycle: int = _get_int("DB_POOL_RECYCLE", 1800)

    r2_account_id: str = os.getenv("R2_ACCOUNT_ID", "")
    r2_access_key_id: str = os.getenv("R2_ACCESS_KEY_ID", "")
    r2_secret_access_key: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    r2_bucket: str = os.getenv("R2_BUCKET", "quotation-v2")
    r2_region: str = os.getenv("R2_REGION", "auto")
    r2_endpoint: str = os.getenv("R2_ENDPOINT", "")
    r2_public_base_url: str = os.getenv("R2_PUBLIC_BASE_URL", "")

    media_sync_dir: str = os.getenv("MEDIA_SYNC_DIR", "/data/media-sync/inbox")
    media_cache_dir: str = os.getenv("MEDIA_CACHE_DIR", "/data/media-sync/cache")
    media_preview_max_width: int = _get_int("MEDIA_PREVIEW_MAX_WIDTH", 480)
    media_preview_max_height: int = _get_int("MEDIA_PREVIEW_MAX_HEIGHT", 320)
    media_preview_quality: int = _get_int("MEDIA_PREVIEW_QUALITY", 82)

    @property
    def resolved_r2_endpoint(self) -> str:
        if self.r2_endpoint:
            return _normalize_endpoint_url(self.r2_endpoint)
        if self.r2_account_id:
            return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"
        return ""


settings = Settings()


def is_production_environment() -> bool:
    explicit_environment = os.getenv("ENVIRONMENT")
    if explicit_environment is not None:
        return explicit_environment.strip().lower() == "production"

    vercel_environment = os.getenv("VERCEL_ENV")
    if vercel_environment is not None:
        return vercel_environment.strip().lower() == "production"

    return os.getenv("VERCEL") == "1"
