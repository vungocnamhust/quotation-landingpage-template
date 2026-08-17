"""Validate production runtime settings and explicit fresh-start cutovers.

Routine deployments must not inspect or rewrite canonical quotation data.  The
fresh-start guard remains fail-closed, but is reserved for the operator-run
cutover job that provisions a new V2 database.
"""
from __future__ import annotations

import asyncio
import os
from urllib.parse import urlsplit

from sqlalchemy import text

from db.session import get_session_factory


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off", ""}
_DEFAULT_PUBLIC_BRAND_HOSTS = (
    "journeys.capellatravel.com",
    "my.selvarajourneys.com",
    "journeys.vietnamsafar.vn",
)


def _strict_env_bool(name: str, *, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in _TRUE_VALUES:
        return True
    if normalized in _FALSE_VALUES:
        return False
    raise RuntimeError(f"{name} must be a boolean (true/false), got {raw_value!r}.")


def validate_runtime_security() -> None:
    """Validate mutually-exclusive ingress/auth settings.

    This is deliberately independent from the imported Settings singleton so a
    deployment preflight observes the actual process environment and tests can
    exercise both modes without reloading the application.
    """
    gateway_enabled = _strict_env_bool("DMC_GATEWAY_ENABLED")
    trust_cloudflare = _strict_env_bool("QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS")
    service_token = os.getenv("QUOTE_SERVICE_TOKEN", "").strip()
    if not service_token or service_token in {"replace_me", "change-me", "changeme"}:
        raise RuntimeError("QUOTE_SERVICE_TOKEN must be a non-placeholder secret in production.")

    if gateway_enabled:
        parsed_proxy = urlsplit(os.getenv("DMC_AUTH_PROXY_URL", "").strip())
        if parsed_proxy.scheme not in {"http", "https"} or not parsed_proxy.netloc:
            raise RuntimeError("Production gateway mode requires a valid DMC_AUTH_PROXY_URL.")
        if trust_cloudflare:
            raise RuntimeError("DMC gateway mode must not enable direct Cloudflare Access JWT fallback.")
    else:
        if not trust_cloudflare:
            raise RuntimeError("Direct Cloudflare Access mode requires QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS=true.")
        team_domain = os.getenv("CLOUDFLARE_ACCESS_TEAM_DOMAIN", "").strip().lower()
        audience = os.getenv("CLOUDFLARE_ACCESS_AUDIENCE", "").strip()
        if not team_domain or not audience or audience in {"replace_with_access_application_aud", "change-me"}:
            raise RuntimeError("Direct Cloudflare Access mode requires CLOUDFLARE_ACCESS_TEAM_DOMAIN and CLOUDFLARE_ACCESS_AUDIENCE.")

    configured_hosts = os.getenv("PUBLIC_BRAND_HOSTS", " ".join(_DEFAULT_PUBLIC_BRAND_HOSTS))
    hosts = tuple(item.strip().lower() for item in configured_hosts.split() if item.strip())
    if not hosts or any("/" in host or ":" in host or " " in host for host in hosts):
        raise RuntimeError("PUBLIC_BRAND_HOSTS must contain one or more bare hostnames separated by spaces.")
    fallback_host = os.getenv("PUBLIC_FALLBACK_HOSTNAME", "quotes.capellatravel.com").strip().lower()
    if not fallback_host or "/" in fallback_host or ":" in fallback_host or " " in fallback_host:
        raise RuntimeError("PUBLIC_FALLBACK_HOSTNAME must be a bare hostname.")
    if fallback_host in hosts:
        raise RuntimeError("PUBLIC_FALLBACK_HOSTNAME must not be an active brand hostname.")


def validate_fresh_start_intent() -> None:
    """Require an explicit acknowledgement before inspecting a fresh database."""
    if not _strict_env_bool("V2_PRODUCTION_FRESH_START"):
        raise RuntimeError("V2_PRODUCTION_FRESH_START=true is required for a fresh V2 production database.")


async def _table_exists(session, table: str) -> bool:
    return bool(await session.scalar(text("SELECT to_regclass(:table) IS NOT NULL"), {"table": f"public.{table}"}))


async def validate_fresh_start_database() -> None:
    """Fail if an explicit fresh-start cutover targets existing quotation data."""
    if os.getenv("ENVIRONMENT", "local").strip().lower() != "production":
        return
    validate_runtime_security()
    validate_fresh_start_intent()
    async with get_session_factory()() as session:
        legacy_tables = [table for table in ("quotations", "quotation_publications") if await _table_exists(session, table)]
        for table in legacy_tables:
            count = await session.scalar(text(f"SELECT COUNT(*) FROM {table}"))
            if count:
                raise RuntimeError(
                    f"Production V2 fresh-start preflight failed: {table} contains {count} row(s). "
                    "This deploy never migrates legacy quotations; provision a clean database or perform an approved manual archive."
                )


async def main() -> None:
    await validate_fresh_start_database()


if __name__ == "__main__":
    asyncio.run(main())
