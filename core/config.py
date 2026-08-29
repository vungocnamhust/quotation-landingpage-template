from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

# Container environments are the deployment source of truth. Loading a checked
# out .env.local with override=True inside Compose silently replaces DATABASE_URL
# and production credentials with a developer machine's values.
if os.getenv("ENVIRONMENT", "local").strip().lower() in {"local", "development", "dev"} and os.path.exists(".env.local"):
    load_dotenv(".env.local", override=True)
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
    media_library_prefixes: tuple[str, ...] = tuple(
        item.strip().strip("/")
        for item in os.getenv("MEDIA_LIBRARY_PREFIXES", "shared/media,library/media").split(",")
        if item.strip().strip("/")
    )
    media_library_country_roots: tuple[str, ...] = tuple(
        item.strip().strip("/")
        for item in os.getenv("MEDIA_LIBRARY_COUNTRY_ROOTS", "vietnam,cambodia,laos,thailand").split(",")
        if item.strip().strip("/")
    )
    media_library_preview_concurrency: int = _get_int("MEDIA_LIBRARY_PREVIEW_CONCURRENCY", 3)
    publication_job_max_attempts: int = _get_int("PUBLICATION_JOB_MAX_ATTEMPTS", 5)
    publication_job_backoff_base_seconds: int = _get_int("PUBLICATION_JOB_BACKOFF_BASE_SECONDS", 30)
    publication_job_backoff_max_seconds: int = _get_int("PUBLICATION_JOB_BACKOFF_MAX_SECONDS", 900)
    publication_job_lease_seconds: int = _get_int("PUBLICATION_JOB_LEASE_SECONDS", 300)
    publication_worker_poll_seconds: int = _get_int("PUBLICATION_WORKER_POLL_SECONDS", 2)
    public_fallback_hostname: str = os.getenv("PUBLIC_FALLBACK_HOSTNAME", "quotes.capellatravel.com").strip().lower().rstrip(".")
    public_media_origin: str | None = os.getenv("PUBLIC_MEDIA_ORIGIN") if os.getenv("PUBLIC_MEDIA_ORIGIN") else None
    cdn_purge_enabled: bool = _get_bool(
        "CDN_PURGE_ENABLED",
        bool(os.getenv("CLOUDFLARE_ZONE_ID", "").strip() and os.getenv("CLOUDFLARE_API_TOKEN", "").strip()),
    )
    dmc_gateway_enabled: bool = _get_bool("DMC_GATEWAY_ENABLED", False)
    dmc_auth_proxy_url: str = os.getenv("DMC_AUTH_PROXY_URL", "").strip()
    cloudflare_access_team_domain: str = os.getenv("CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip().lower()
    cloudflare_access_audience: str = os.getenv("CLOUDFLARE_ACCESS_AUDIENCE", "").strip()

    @property
    def media_library_roots(self) -> tuple[str, ...]:
        """Every browseable root must also be included in an R2 sync run."""
        return tuple(
            dict.fromkeys(
                ("shared/media", "library/media", *self.media_library_prefixes, *self.media_library_country_roots, "accommodations", "team")
            )
        )

    @property
    def resolved_r2_endpoint(self) -> str:
        if self.r2_endpoint:
            return _normalize_endpoint_url(self.r2_endpoint)
        if self.r2_account_id:
            return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"
        return ""

    @property
    def has_r2_configuration(self) -> bool:
        return bool(
            self.r2_access_key_id
            and self.r2_secret_access_key
            and self.resolved_r2_endpoint
            and self.r2_bucket
        )

    @property
    def cloudflare_access_jwks_url(self) -> str:
        if not self.cloudflare_access_team_domain:
            return ""
        return f"https://{self.cloudflare_access_team_domain}/cdn-cgi/access/certs"


settings = Settings()


def is_production_environment() -> bool:
    explicit_environment = os.getenv("ENVIRONMENT")
    if explicit_environment is not None:
        return explicit_environment.strip().lower() == "production"

    vercel_environment = os.getenv("VERCEL_ENV")
    if vercel_environment is not None:
        return vercel_environment.strip().lower() == "production"

    return os.getenv("VERCEL") == "1"
