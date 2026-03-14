"""Tests for the errors analysis check."""

from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.errors import ErrorsCheck


def _make_check(url: str = "https://example.com") -> ErrorsCheck:
    return ErrorsCheck(url=url)


def _mock_response(status: int = 200, text: str = "", content_type: str = "text/html", headers: dict | None = None) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    all_headers = {"content-type": content_type}
    if headers:
        all_headers.update(headers)
    resp.headers = all_headers
    resp.json = lambda: __import__("json").loads(text) if text else {}
    return resp


class TestNotFoundQuality:
    def test_structured_json_404(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(
            status=404,
            text='{"error": "not_found", "message": "Resource not found"}',
            content_type="application/json",
        )
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_404_quality("https://example.com", details)
        assert score == 1.0
        assert details["404_is_json"]

    def test_html_404(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(status=404, text="<html><body><h1>Not Found</h1></body></html>")
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_404_quality("https://example.com", details)
        assert score == 0.3

    def test_soft_404(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(status=200, text="<html><body>Page not found</body></html>")
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_404_quality("https://example.com", details)
        assert score == 0.1
        assert details.get("soft_404")


class TestRateLimitHeaders:
    def test_full_rate_limit(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(headers={
            "x-ratelimit-limit": "100",
            "x-ratelimit-remaining": "99",
            "x-ratelimit-reset": "1609459200",
        })
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_rate_limit_headers("https://example.com", details)
        assert score == 1.0

    def test_no_rate_limit(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response()
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_rate_limit_headers("https://example.com", details)
        assert score == 0.0

    def test_retry_after_only(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(headers={"retry-after": "60"})
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_rate_limit_headers("https://example.com", details)
        assert score == 0.6


class TestMethodHandling:
    def test_proper_405(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(status=405, headers={"allow": "GET, HEAD, OPTIONS"})
        with patch("httpx.delete", return_value=resp):
            score, findings = check._check_method_handling("https://example.com", details)
        assert score == 1.0
        assert "Allow" in findings[0]

    def test_accepts_delete(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(status=200)
        with patch("httpx.delete", return_value=resp):
            score, findings = check._check_method_handling("https://example.com", details)
        assert score == 0.3
