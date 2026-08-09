"""Compose proof that Nginx owns DMC identity headers in gateway mode."""
from __future__ import annotations

import os
from urllib.error import HTTPError
from urllib.request import Request, urlopen


EDITOR_BASE = os.environ["E2E_EDITOR_BASE_URL"].rstrip("/")


def status(headers: dict[str, str]) -> int:
    request = Request(f"{EDITOR_BASE}/api/v2/brands", headers=headers)
    try:
        with urlopen(request, timeout=10) as response:
            return response.status
    except HTTPError as error:
        return error.code


def main() -> None:
    # A browser cannot authenticate by inventing a DMC header or an arbitrary
    # Cloudflare JWT while gateway mode is enabled.
    assert status({"X-DMC-Email": "spoofed@example.test"}) == 401
    assert status({"Cf-Access-Jwt-Assertion": "not-a-gateway-session"}) == 401

    # The only accepted identity is produced by the auth_request upstream.
    approved_status = status({"X-DMC-Mock-Session": "approved", "X-DMC-Email": "spoofed@example.test"})
    if approved_status != 200:
        raise AssertionError(f"approved gateway session was rejected with HTTP {approved_status}")


if __name__ == "__main__":
    main()
