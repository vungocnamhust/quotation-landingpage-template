from pathlib import Path
import re
import unittest
from unittest.mock import patch
import os

from scripts.production_preflight import validate_fresh_start_intent, validate_runtime_security
import scripts.production_preflight as production_preflight


ROOT = Path(__file__).resolve().parents[1]


class V2IngressContractTests(unittest.TestCase):
    def test_public_branded_hosts_allow_only_the_map_tile_api_route(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        public_server = config.split("server_name ${PUBLIC_BRAND_HOSTS}", 1)[1]
        self.assertIn("location ^~ /api/map-tiles/", public_server)
        self.assertNotIn("location ^~ /api/v2/", public_server)
        self.assertNotIn("location /internal/", public_server)
        self.assertIn("location / { return 404; }", public_server)
        fallback = (ROOT / "docker/nginx/default.conf").read_text()
        fallback_public = fallback.split("server_name journeys.capellatravel.com", 1)[1]
        self.assertIn("location ^~ /api/map-tiles/", fallback_public)
        self.assertNotIn("location ^~ /api/v2/", fallback_public)
        self.assertNotIn("location /internal/", fallback_public)

    def test_public_host_allowlist_is_runtime_configured(self):
        template = (ROOT / "docker/nginx/default.conf.template").read_text()
        envsh = (ROOT / "docker/nginx/10-dmc-gateway-mode.envsh").read_text()
        self.assertIn("server_name ${PUBLIC_BRAND_HOSTS};", template)
        self.assertIn("PUBLIC_BRAND_HOSTS", envsh)

    def test_public_fallback_host_exposes_release_media_and_map_tiles_only(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        fallback_server = config.split("server_name ${PUBLIC_FALLBACK_HOSTNAME};", 1)[1].split("server_name quote.capellatravel.com;", 1)[0]
        self.assertIn("location ~ ^/p/[^/]+/", fallback_server)
        self.assertIn("location ^~ /media/", fallback_server)
        self.assertIn("location ^~ /api/map-tiles/", fallback_server)
        self.assertNotIn("location ^~ /api/v2/", fallback_server)
        self.assertNotIn("/internal/", fallback_server)
        self.assertIn("location / { return 404; }", fallback_server)

    def test_fallback_hostname_is_templated_and_quote_ingress_has_dmc_alias(self):
        envsh = (ROOT / "docker/nginx/10-dmc-gateway-mode.envsh").read_text()
        compose = (ROOT / "docker-compose.production.yml").read_text()
        self.assertIn("PUBLIC_FALLBACK_HOSTNAME", envsh)
        self.assertIn("quotation-ingress", compose)

    def test_production_direct_cloudflare_mode_is_validated(self):
        with patch.dict(
            os.environ,
            {
                "DMC_GATEWAY_ENABLED": "false",
                "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
                "CLOUDFLARE_ACCESS_TEAM_DOMAIN": "team.example.cloudflareaccess.com",
                "CLOUDFLARE_ACCESS_AUDIENCE": "audience-1",
                "QUOTE_SERVICE_TOKEN": "a-real-secret",
                "PUBLIC_BRAND_HOSTS": "journeys.example.com",
                "PUBLIC_FALLBACK_HOSTNAME": "quotes.example.com",
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
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "must not enable"):
                validate_runtime_security()

    def test_fresh_start_intent_is_an_explicit_cutover_requirement(self):
        with patch.dict(
            os.environ,
            {
                "DMC_GATEWAY_ENABLED": "false",
                "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
                "CLOUDFLARE_ACCESS_TEAM_DOMAIN": "team.example.cloudflareaccess.com",
                "CLOUDFLARE_ACCESS_AUDIENCE": "audience-1",
                "QUOTE_SERVICE_TOKEN": "a-real-secret",
                "V2_PRODUCTION_FRESH_START": "false",
            },
            clear=True,
        ):
            validate_runtime_security()
            with self.assertRaisesRegex(RuntimeError, "FRESH_START"):
                validate_fresh_start_intent()

    def test_fresh_start_cutover_rejects_existing_quotation_rows(self):
        class FakeSession:
            async def scalar(self, statement, *_args, **_kwargs):
                return 1 if "COUNT" in str(statement) else True

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

        class FakeSessionFactory:
            def __call__(self):
                return FakeSession()

        cutover_env = {
            "ENVIRONMENT": "production",
            "DMC_GATEWAY_ENABLED": "false",
            "QUOTE_TRUST_CLOUDFLARE_ACCESS_HEADERS": "true",
            "CLOUDFLARE_ACCESS_TEAM_DOMAIN": "team.example.cloudflareaccess.com",
            "CLOUDFLARE_ACCESS_AUDIENCE": "audience-1",
            "QUOTE_SERVICE_TOKEN": "a-real-secret",
            "V2_PRODUCTION_FRESH_START": "true",
            "PUBLIC_BRAND_HOSTS": "journeys.example.com",
            "PUBLIC_FALLBACK_HOSTNAME": "quotes.example.com",
        }
        with patch.dict(os.environ, cutover_env, clear=True), patch.object(production_preflight, "get_session_factory", return_value=FakeSessionFactory()):
            with self.assertRaisesRegex(RuntimeError, "quotations contains 1 row"):
                import asyncio

                asyncio.run(production_preflight.validate_fresh_start_database())

    def test_production_manifest_keeps_cutover_jobs_out_of_runtime_dependencies(self):
        compose = (ROOT / "docker-compose.production.yml").read_text()
        migrate = compose.split("  migrate:\n", 1)[1].split("\n  v2-cutover-preflight:", 1)[0]
        self.assertIn("alembic upgrade head && alembic current --check-heads", migrate)
        self.assertNotIn("production_preflight", migrate)
        self.assertNotIn("migrate_v2_rich_content", migrate)
        for service in ("v2-cutover-preflight", "v2-rich-content-report", "v2-rich-content-apply"):
            match = re.search(rf"^  {re.escape(service)}:(.*?)(?=^  \S|\Z)", compose, re.MULTILINE | re.DOTALL)
            self.assertIsNotNone(match)
            block = match.group(1)
            self.assertIn('profiles: ["cutover"]', block)
            self.assertNotIn("dmc-network", block)

    def test_editor_identity_uses_one_feature_flagged_auth_boundary(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        self.assertIn("auth_request ${DMC_AUTH_REQUEST_URI};", config)
        self.assertIn('proxy_set_header X-Quote-Service-Token "";', config)
        auth = (ROOT / "core/auth.py").read_text()
        self.assertIn("not _is_dmc_gateway_enabled()", auth)

    def test_workspace_route_does_not_trigger_nginx_trailing_slash_redirect(self):
        config = (ROOT / "docker/nginx/default.conf.template").read_text()
        self.assertIn("location ~ ^/workspace(?:/|$) {", config)
        self.assertNotIn("location ^~ /workspace/ {", config)

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
