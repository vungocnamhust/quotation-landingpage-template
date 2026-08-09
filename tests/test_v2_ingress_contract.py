from pathlib import Path
import unittest
from unittest.mock import patch
import os

from scripts.production_preflight import validate_runtime_security


ROOT = Path(__file__).resolve().parents[1]


class V2IngressContractTests(unittest.TestCase):
    def test_public_branded_hosts_have_no_api_or_internal_proxy(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        public_server = config.split("server_name ${PUBLIC_BRAND_HOSTS}", 1)[1]
        self.assertNotIn("location /api/", public_server)
        self.assertNotIn("location /internal/", public_server)
        self.assertIn("location / { return 404; }", public_server)
        fallback = (ROOT / "docker/nginx/default.conf").read_text()
        fallback_public = fallback.split("server_name journeys.capellatravel.com", 1)[1]
        self.assertNotIn("location /api/", fallback_public)
        self.assertNotIn("location /internal/", fallback_public)

    def test_public_host_allowlist_is_runtime_configured(self):
        template = (ROOT / "docker/nginx/default.conf.template").read_text()
        envsh = (ROOT / "docker/nginx/10-dmc-gateway-mode.envsh").read_text()
        self.assertIn("server_name ${PUBLIC_BRAND_HOSTS};", template)
        self.assertIn("PUBLIC_BRAND_HOSTS", envsh)

    def test_production_direct_cloudflare_mode_is_validated(self):
        with patch.dict(
            os.environ,
            {
                "DMC_GATEWAY_ENABLED": "false",
                "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
                "CLOUDFLARE_ACCESS_TEAM_DOMAIN": "team.example.cloudflareaccess.com",
                "CLOUDFLARE_ACCESS_AUDIENCE": "audience-1",
                "QUOTE_SERVICE_TOKEN": "a-real-secret",
                "V2_PRODUCTION_FRESH_START": "true",
                "PUBLIC_BRAND_HOSTS": "journeys.example.com",
            },
            clear=True,
        ):
            validate_runtime_security()

    def test_production_dmc_mode_is_mutually_exclusive_with_cloudflare_bridge(self):
        with patch.dict(
            os.environ,
            {
                "DMC_GATEWAY_ENABLED": "true",
                "DMC_AUTH_PROXY_URL": "http://dmc-auth-proxy:8120/verify",
                "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
                "QUOTE_SERVICE_TOKEN": "a-real-secret",
                "V2_PRODUCTION_FRESH_START": "true",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "must not enable"):
                validate_runtime_security()

    def test_production_preflight_rejects_missing_fresh_start_and_placeholder_secret(self):
        with patch.dict(
            os.environ,
            {
                "DMC_GATEWAY_ENABLED": "false",
                "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
                "CLOUDFLARE_ACCESS_TEAM_DOMAIN": "team.example.cloudflareaccess.com",
                "CLOUDFLARE_ACCESS_AUDIENCE": "audience-1",
                "QUOTE_SERVICE_TOKEN": "replace_me",
                "V2_PRODUCTION_FRESH_START": "false",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "FRESH_START"):
                validate_runtime_security()

    def test_editor_identity_uses_one_feature_flagged_auth_boundary(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        self.assertIn("auth_request ${DMC_AUTH_REQUEST_URI};", config)
        self.assertIn('proxy_set_header X-Quote-Service-Token "";', config)
        auth = (ROOT / "core/auth.py").read_text()
        self.assertIn("not _is_dmc_gateway_enabled()", auth)

    def test_template_has_no_direct_service_token_or_identity_header_passthrough(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        self.assertGreaterEqual(config.count('proxy_set_header X-Quote-Service-Token "";'), 4)
        self.assertIn('proxy_set_header X-DMC-Email $auth_email;', config)
        self.assertNotIn('proxy_set_header X-DMC-Email $http_x_dmc_email;', config)

    def test_rendered_ingress_gate_checks_both_auth_modes_and_all_service_ports(self):
        script = (ROOT / "scripts/verify_production_ingress.sh").read_text()
        self.assertIn("-e DMC_GATEWAY_ENABLED=true", script)
        self.assertIn("-e DMC_GATEWAY_ENABLED=false", script)
        self.assertIn("for name, service in services.items()", script)
        self.assertIn("must not publish host ports in production", script)


if __name__ == "__main__":
    unittest.main()
