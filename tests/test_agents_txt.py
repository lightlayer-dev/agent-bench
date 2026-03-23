"""Tests for the agents_txt analysis check."""

from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.agents_txt import AgentsTxtCheck


def _make_check(url: str = "https://example.com") -> AgentsTxtCheck:
    return AgentsTxtCheck(url=url)


def _mock_response(
    status: int = 200, text: str = "", content_type: str = "text/plain"
) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    resp.headers = {"content-type": content_type}
    return resp


class TestPresence:
    def test_no_agents_txt(self):
        check = _make_check()
        with patch.object(check, "_fetch", return_value=None):
            result = check.execute()
        assert result.score == 0.0
        assert not result.details["agents_txt_found"]

    def test_agents_txt_at_root(self):
        content = (
            "User-agent: *\n"
            "Allow: /api\n"
            "Disallow: /admin\n"
            "Rate-limit: 100/minute\n"
            "Contact: agents@example.com\n"
        )

        def mock_fetch(url):
            if "/agents.txt" in url and "well-known" not in url:
                return _mock_response(text=content)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["agents_txt_found"]
        assert result.details["agents_txt_path"] == "/agents.txt"
        assert result.score > 0.5

    def test_agents_txt_at_well_known(self):
        content = "Agent: GPTBot\nAllow: /\n"

        def mock_fetch(url):
            if "/.well-known/agents.txt" in url:
                return _mock_response(text=content)
            return _mock_response(status=404, text="")

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["agents_txt_found"]
        assert result.details["agents_txt_path"] == "/.well-known/agents.txt"

    def test_html_page_not_agents_txt(self):
        """HTML pages at /agents.txt should not count."""

        def mock_fetch(url):
            return _mock_response(
                text="<html><body>Not found</body></html>",
                content_type="text/html; charset=utf-8",
            )

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert not result.details["agents_txt_found"]


class TestQuality:
    def test_full_quality(self):
        content = (
            "User-agent: *\n"
            "Allow: /api\n"
            "Disallow: /admin\n"
            "Rate-limit: 100/minute\n"
            "Contact: agents@example.com\n"
            "Payment: x402\n"
        )

        def mock_fetch(url):
            if "/agents.txt" in url:
                return _mock_response(text=content)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["agents_txt_has_blocks"]
        assert result.details["agents_txt_has_permissions"]
        assert result.details["agents_txt_has_rate_limits"]
        assert result.details["agents_txt_has_contact"]
        assert result.details["agents_txt_has_payment"]
        assert result.score >= 0.9

    def test_minimal_agents_txt(self):
        content = "# Our agents policy\nSee /docs for details\n"

        def mock_fetch(url):
            if "/agents.txt" in url and "well-known" not in url:
                return _mock_response(text=content)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["agents_txt_found"]
        # Found but low quality
        assert result.score < 0.7
