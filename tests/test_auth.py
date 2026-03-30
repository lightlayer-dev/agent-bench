"""Tests for the auth analysis check."""

from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.auth import AuthCheck


def _make_check(url: str = "https://example.com") -> AuthCheck:
    return AuthCheck(url=url)


def _mock_response(
    status: int = 200,
    text: str = "",
    content_type: str = "text/html",
    headers: dict | None = None,
) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    all_headers = {"content-type": content_type}
    if headers:
        all_headers.update(headers)
    resp.headers = all_headers
    resp.json = lambda: __import__("json").loads(text) if text else {}
    return resp


class TestBotDetection:
    def test_no_waf(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(text="<html><body>Hello</body></html>")
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_bot_detection("https://example.com", details)
        assert score == 1.0
        assert details["bot_detection"] == []

    def test_passive_cloudflare(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(
            text="<html><body>Hello</body></html>",
            headers={"cf-ray": "abc123", "cf-cache-status": "HIT"},
        )
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_bot_detection("https://example.com", details)
        assert score == 0.8
        assert "Cloudflare" in details["bot_detection"]

    def test_active_cloudflare_challenge(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(
            text="<html>challenge-platform cf-challenge</html>",
            headers={"cf-ray": "abc123"},
        )
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_bot_detection("https://example.com", details)
        assert score == 0.1


class TestCaptcha:
    def test_no_captcha(self):
        check = _make_check()
        details: dict = {}

        def mock_fetch(url, **kwargs):
            return _mock_response(
                text="<html><body><form><input type='text'></form></body></html>"
            )

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_captcha("https://example.com", details)
        assert score == 1.0

    def test_recaptcha_detected(self):
        check = _make_check()
        details: dict = {}

        def mock_fetch(url, **kwargs):
            if "/login" in url:
                return _mock_response(
                    text='<html><div class="g-recaptcha" data-sitekey="abc"></div></html>'
                )
            return _mock_response(text="<html><body>Main page</body></html>")

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_captcha("https://example.com", details)
        assert score == 0.2
        assert "g-recaptcha" in details["captcha_detected"]


class TestOAuthDiscovery:
    def test_oidc_with_client_credentials(self):
        check = _make_check()
        details: dict = {}
        oidc = '{"issuer": "https://example.com", "grant_types_supported": ["authorization_code", "client_credentials"]}'

        def mock_fetch(url, **kwargs):
            if "openid-configuration" in url:
                return _mock_response(text=oidc, content_type="application/json")
            return _mock_response(status=404)

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_oauth_discovery(
                "https://example.com", details
            )
        assert score == 1.0
        assert "client_credentials" in str(findings)

    def test_no_oauth(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=_mock_response(status=404)):
            score, findings = check._check_oauth_discovery(
                "https://example.com", details
            )
        assert score == 0.5  # Neutral — might use API keys


class TestLoginForm:
    def test_no_login(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=_mock_response(status=404)):
            score, findings = check._check_login_form("https://example.com", details)
        assert score == 0.8  # No login = good for agents

    def test_simple_login(self):
        check = _make_check()
        details: dict = {}
        html = '<html><body><form><input type="email" name="email"><input type="password" name="password"><button>Login</button></form></body></html>'

        def mock_fetch(url, **kwargs):
            if "/login" in url:
                return _mock_response(text=html)
            return _mock_response(status=404)

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_login_form("https://example.com", details)
        assert score == 0.6
        assert details["login_form_found"]
