from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request, status
from core.config import settings

try:
    import jwt
    from jwt import PyJWKClient
except ImportError:  # pragma: no cover - production image always installs requirements.txt
    jwt = None
    PyJWKClient = None


_jwks_client = None


@dataclass(frozen=True)
class Principal:
    email: str | None
    person_id: str | None = None
    brand: str | None = None
    role: str | None = None
    source: str = "local"
    is_service: bool = False


def _normalize_email(value: str | None) -> str | None:
    value = (value or "").strip().lower()
    return value or None


def _is_local_bypass_allowed() -> bool:
    return (
        os.getenv("ENVIRONMENT", "local").strip().lower() != "production"
        and os.getenv("QUOTE_AUTH_REQUIRED", "false").strip().lower() not in {"1", "true", "yes", "on"}
    )


def _is_dmc_gateway_enabled() -> bool:
    """Keep the two production identity boundaries mutually exclusive."""
    return os.getenv("DMC_GATEWAY_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _validate_cloudflare_access_jwt(token: str) -> str | None:
    """Return the verified Access identity; never trust the email header alone."""
    global _jwks_client
    if not settings.cloudflare_access_team_domain or not settings.cloudflare_access_audience or jwt is None or PyJWKClient is None:
        return None
    try:
        if _jwks_client is None:
            _jwks_client = PyJWKClient(settings.cloudflare_access_jwks_url)
        signing_key = _jwks_client.get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=settings.cloudflare_access_audience,
            issuer=f"https://{settings.cloudflare_access_team_domain}",
        )
    except Exception:
        return None
    return _normalize_email(claims.get("email") if isinstance(claims, dict) else None)


def get_principal(request: Request, *, allow_service: bool = False) -> Principal:
    service_token = request.headers.get("X-Quote-Service-Token")
    configured_token = os.getenv("QUOTE_SERVICE_TOKEN", "")
    if allow_service and service_token and configured_token and hmac.compare_digest(service_token, configured_token):
        return Principal(email=None, source="service_token", is_service=True)

    email = _normalize_email(request.headers.get("X-DMC-Email"))
    if _is_dmc_gateway_enabled() and email:
        return Principal(
            email=email,
            person_id=request.headers.get("X-DMC-Person-Id") or None,
            brand=request.headers.get("X-DMC-Brand") or None,
            role=request.headers.get("X-DMC-Role") or None,
            source="dmc_gateway",
        )

    # Transitional production path: Cloudflare Access protects the editor host
    # before its requests are moved behind dmc-auth-proxy. This is deliberately
    # opt-in; origin access must remain Cloudflare-only while it is enabled.
    if not _is_dmc_gateway_enabled() and os.getenv("QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS", "false").strip().lower() in {"1", "true", "yes", "on"}:
        cf_email = _validate_cloudflare_access_jwt(request.headers.get("Cf-Access-Jwt-Assertion", ""))
        if cf_email:
            return Principal(email=cf_email, source="cloudflare_access")

    if _is_local_bypass_allowed():
        return Principal(email="local@localhost", source="local")
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_editor(request: Request) -> Principal:
    principal = get_principal(request)
    if principal.is_service:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Interactive editor identity required")
    return principal


def require_editor_or_service(request: Request) -> Principal:
    return get_principal(request, allow_service=True)


def require_quote_admin(request: Request) -> Principal:
    """Require a gateway editor explicitly granted quote administration.

    Profile provisioning changes identity bindings and must not be exposed to a
    normal Travel Designer merely because they can edit their own quotations.
    """
    principal = require_editor(request)
    if principal.source == "local":
        # Local development deliberately has no gateway role header. Production
        # never reaches this branch because local bypass is disabled there.
        return principal
    configured_roles = {
        role.strip().lower()
        for role in os.getenv("QUOTE_ADMIN_ROLES", "quote_admin").split(",")
        if role.strip()
    }
    roles = {
        role.strip().lower()
        for role in (principal.role or "").split(",")
        if role.strip()
    }
    if not configured_roles.intersection(roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Quote administrator role required")
    return principal
