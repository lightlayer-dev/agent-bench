"""Tests for the docs analysis check."""

from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.docs import DocsCheck


def _make_check(url: str = "https://example.com") -> DocsCheck:
    return DocsCheck(url=url)


def _mock_response(status: int = 200, text: str = "", content_type: str = "text/plain") -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    resp.headers = {"content-type": content_type}
    resp.json = lambda: __import__("json").loads(text) if text else {}
    return resp


class TestRobots:
    def test_no_robots(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=None):
            score, findings = check._check_robots("https://example.com", details)
        assert score == 0.0
        assert not details["robots_txt"]

    def test_permissive_robots(self):
        check = _make_check()
        details: dict = {}
        robots = "User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml"
        with patch.object(check, "_fetch", return_value=_mock_response(text=robots)):
            score, findings = check._check_robots("https://example.com", details)
        assert score == 1.0
        assert details["robots_has_sitemap_ref"]

    def test_blocks_ai_bots(self):
        check = _make_check()
        details: dict = {}
        robots = "User-agent: *\nAllow: /\n\nUser-agent: GPTBot\nDisallow: /api"
        with patch.object(check, "_fetch", return_value=_mock_response(text=robots)):
            score, findings = check._check_robots("https://example.com", details)
        assert score < 0.8
        assert "gptbot" in details["blocked_ai_bots"]


class TestSitemap:
    def test_valid_sitemap(self):
        check = _make_check()
        details: dict = {}
        sitemap = '<?xml version="1.0"?><urlset><url><loc>https://example.com/</loc></url><url><loc>https://example.com/about</loc></url></urlset>'
        with patch.object(check, "_fetch", return_value=_mock_response(text=sitemap, content_type="application/xml")):
            score, findings = check._check_sitemap("https://example.com", details)
        assert score == 1.0
        assert details["sitemap_urls"] == 2

    def test_no_sitemap(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=_mock_response(status=404)):
            score, findings = check._check_sitemap("https://example.com", details)
        assert score == 0.0


class TestStructuredData:
    def test_json_ld_present(self):
        check = _make_check()
        details: dict = {}
        html = '<html><head><script type="application/ld+json">{"@type": "Organization", "name": "Test"}</script></head><body></body></html>'
        with patch.object(check, "_fetch", return_value=_mock_response(text=html, content_type="text/html")):
            score, findings = check._check_structured_data("https://example.com", details)
        assert score == 1.0
        assert "Organization" in details["json_ld_types"]


class TestLlmsTxt:
    def test_llms_txt_found(self):
        check = _make_check()
        details: dict = {}
        content = "# LLMs.txt\n\nThis site provides AI-friendly documentation.\n\n## Endpoints\n..."

        def mock_fetch(url):
            if "/llms.txt" in url:
                return _mock_response(text=content)
            return _mock_response(status=404)

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_llms_txt("https://example.com", details)
        assert score == 1.0

    def test_no_llms_txt(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=_mock_response(status=404)):
            score, findings = check._check_llms_txt("https://example.com", details)
        assert score == 0.0
