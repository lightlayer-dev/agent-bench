"""Tests for the A2A Agent Card analysis check."""

import json
from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.a2a import A2ACheck


def _make_check(url: str = "https://example.com") -> A2ACheck:
    return A2ACheck(url=url)


def _mock_response(
    status: int = 200, text: str = "", content_type: str = "application/json"
) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    resp.headers = {"content-type": content_type}
    resp.json = lambda: json.loads(text) if text else {}
    return resp


FULL_AGENT_CARD = json.dumps({
    "name": "Example Agent",
    "description": "A helpful agent that does things",
    "url": "https://example.com/agent",
    "version": "1.0.0",
    "provider": {"organization": "Example Inc"},
    "skills": [
        {"id": "search", "name": "Search", "description": "Search the web"},
        {"id": "calc", "name": "Calculate", "description": "Do math"},
    ],
    "authentication": {"schemes": ["bearer"]},
    "defaultInputModes": ["text/plain", "application/json"],
})

MINIMAL_AGENT_CARD = json.dumps({"name": "Mini Agent"})


class TestPresence:
    def test_no_agent_card(self):
        check = _make_check()
        with patch.object(check, "_fetch", return_value=None):
            result = check.execute()
        assert result.score == 0.0
        assert not result.details["a2a_found"]

    def test_agent_card_at_well_known(self):
        def mock_fetch(url):
            if "/.well-known/agent.json" in url:
                return _mock_response(text=FULL_AGENT_CARD)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["a2a_found"]
        assert result.details["a2a_path"] == "/.well-known/agent.json"
        assert result.score > 0.7

    def test_agent_card_json_fallback(self):
        def mock_fetch(url):
            if "/.well-known/agent-card.json" in url:
                return _mock_response(text=FULL_AGENT_CARD)
            return _mock_response(status=404, text="")

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["a2a_found"]
        assert result.details["a2a_path"] == "/.well-known/agent-card.json"

    def test_html_not_agent_card(self):
        def mock_fetch(url):
            return _mock_response(
                text="<html>Not Found</html>",
                content_type="text/html",
            )

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert not result.details["a2a_found"]


class TestQuality:
    def test_full_quality(self):
        def mock_fetch(url):
            if "agent.json" in url:
                return _mock_response(text=FULL_AGENT_CARD)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["a2a_name"] == "Example Agent"
        assert result.details["a2a_skill_count"] == 2
        assert result.details["a2a_has_auth"]
        assert result.score >= 0.9

    def test_minimal_quality(self):
        def mock_fetch(url):
            if "agent.json" in url:
                return _mock_response(text=MINIMAL_AGENT_CARD)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            result = check.execute()

        assert result.details["a2a_found"]
        assert result.details["a2a_name"] == "Mini Agent"
        # Found but minimal quality (presence=1.0, quality low → avg > 0.5)
        assert result.score < 0.7
