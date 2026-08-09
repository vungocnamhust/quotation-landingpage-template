import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

from core.auth import get_principal


def _request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/api/v2/travel-designers",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
        "query_string": b"",
        "client": ("test", 1),
        "scheme": "http",
        "server": ("test", 80),
    }
    return Request(scope)


class QuoteAuthTests(unittest.TestCase):
    def test_gateway_headers_create_editor_principal(self):
        with patch.dict(os.environ, {"DMC_GATEWAY_ENABLED": "true"}, clear=False):
            principal = get_principal(
                _request(
                    {
                        "X-DMC-Email": " SALE@EXAMPLE.COM ",
                        "X-DMC-Person-Id": "person-1",
                        "X-DMC-Brand": "capella",
                        "X-DMC-Role": "sale",
                    }
                )
            )
        self.assertEqual(principal.email, "sale@example.com")
        self.assertEqual(principal.person_id, "person-1")
        self.assertEqual(principal.source, "dmc_gateway")

    def test_service_token_is_available_only_when_explicitly_allowed(self):
        request = _request({"X-Quote-Service-Token": "secret"})
        with patch.dict(os.environ, {"QUOTE_SERVICE_TOKEN": "secret"}, clear=False):
            principal = get_principal(request, allow_service=True)
            self.assertTrue(principal.is_service)
            with patch.dict(os.environ, {"ENVIRONMENT": "production", "QUOTE_AUTH_REQUIRED": "true"}, clear=False):
                with self.assertRaises(HTTPException):
                    get_principal(request)

    def test_production_without_identity_is_rejected(self):
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "QUOTE_AUTH_REQUIRED": "true"}, clear=False):
            with self.assertRaises(HTTPException):
                get_principal(_request({}))

    @patch("core.auth._validate_cloudflare_access_jwt", return_value="sale@example.com")
    def test_cloudflare_access_bridge_is_explicitly_opt_in(self, _validate_access_jwt):
        request = _request({"Cf-Access-Jwt-Assertion": "signed-token"})
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "QUOTE_AUTH_REQUIRED": "true", "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true"}, clear=False):
            principal = get_principal(request)
        self.assertEqual(principal.email, "sale@example.com")
        self.assertEqual(principal.source, "cloudflare_access")

    def test_cloudflare_email_header_without_signed_token_is_rejected(self):
        request = _request({"Cf-Access-Authenticated-User-Email": "sale@example.com"})
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "QUOTE_AUTH_REQUIRED": "true", "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true"}, clear=False):
                with self.assertRaises(HTTPException):
                    get_principal(request)

    @patch("core.auth._validate_cloudflare_access_jwt", return_value="sale@example.com")
    def test_gateway_mode_has_no_direct_cloudflare_fallback(self, _validate_access_jwt):
        request = _request({"Cf-Access-Jwt-Assertion": "signed-token"})
        with patch.dict(
            os.environ,
            {
                "ENVIRONMENT": "production",
                "QUOTE_AUTH_REQUIRED": "true",
                "DMC_GATEWAY_ENABLED": "true",
                "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
            },
            clear=False,
        ):
            with self.assertRaises(HTTPException):
                get_principal(request)
