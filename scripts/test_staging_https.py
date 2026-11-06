from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
NGINX_CONFIG = ROOT / "deploy" / "nginx" / "qlvb-frontend.conf"
DEPLOY_SCRIPT = ROOT / "deploy" / "deploy.sh"


class StagingHttpsConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = NGINX_CONFIG.read_text(encoding="utf-8")
        cls.deploy_script = DEPLOY_SCRIPT.read_text(encoding="utf-8")

    def test_public_listener_requires_tls_and_certificate_files(self):
        self.assertRegex(self.config, r"(?m)^\s*listen 8088 ssl;")
        self.assertRegex(self.config, r"(?m)^\s*listen \[::\]:8088 ssl;")
        self.assertIn("ssl_certificate /etc/qlvb/tls/fullchain.pem;", self.config)
        self.assertIn("ssl_certificate_key /etc/qlvb/tls/privkey.pem;", self.config)
        self.assertIn("ssl_protocols TLSv1.2 TLSv1.3;", self.config)

    def test_plain_http_on_public_port_redirects_to_canonical_https_origin(self):
        self.assertRegex(
            self.config,
            re.compile(
                r"error_page\s+497\s+=301\s+"
                r"https://staging-quanlyvanban\.bhbl\.vn:8088\$request_uri;"
            ),
        )
        self.assertNotIn(
            "return 301 http://staging-quanlyvanban.bhbl.vn:8088$request_uri;",
            self.config,
        )

    def test_backend_scheme_is_overwritten_from_tls_connection(self):
        self.assertIn("proxy_set_header X-Forwarded-Proto $scheme;", self.config)
        self.assertNotIn("proxy_set_header X-Forwarded-Proto $http_", self.config)

    def test_deploy_requires_explicit_https_backend_settings(self):
        for variable in (
            "DJANGO_SECURE_PROXY_SSL_HEADER",
            "DJANGO_SECURE_SSL_REDIRECT",
            "DJANGO_SECURE_COOKIES",
        ):
            self.assertIn(f'require_true_env "{variable}"', self.deploy_script)
        self.assertIn("https://staging-quanlyvanban.bhbl.vn:8088", self.deploy_script)

    def test_admin_remains_available_only_through_local_ssh_tunnel(self):
        self.assertRegex(self.config, r"(?m)^\s*listen 127\.0\.0\.1:8089;")
        self.assertIn("proxy_set_header X-Forwarded-Proto https;", self.config)
        self.assertRegex(
            self.config,
            re.compile(r"location\s+\^~\s+/admin\s*\{[^}]*proxy_pass", re.DOTALL),
        )


if __name__ == "__main__":
    unittest.main()
