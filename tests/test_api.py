"""Tests for the API analysis check."""

from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.api import APICheck


def _make_check(url: str = "https://example.com") -> APICheck:
    return APICheck(url=url)


def _mock_response(
    status: int = 200,
    text: str = "",
    content_type: str = "application/json",
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


class TestAPIEndpoints:
    def test_no_endpoints(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=_mock_response(status=404)):
            score, findings = check._check_api_endpoints("https://example.com", details)
        assert score == 0.0
        assert details["endpoint_count"] == 0

    def test_json_endpoint_found(self):
        check = _make_check()
        details: dict = {}

        def mock_fetch(url, **kwargs):
            if "/api" in url and "/api/" not in url:
                return _mock_response(text='{"users": []}', content_type="application/json")
            return _mock_response(status=404)

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_api_endpoints("https://example.com", details)
        assert score >= 0.5
        assert details["endpoint_count"] >= 1

    def test_paginated_endpoint(self):
        check = _make_check()
        details: dict = {}

        def mock_fetch(url, **kwargs):
            if "/api" in url:
                return _mock_response(
                    text='{"results": [], "next": "/api?page=2", "count": 100}',
                    content_type="application/json",
                )
            return _mock_response(status=404)

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_api_endpoints("https://example.com", details)
        assert any("pagination" in f for f in findings)


class TestGraphQL:
    def test_graphql_with_introspection(self):
        check = _make_check()
        details: dict = {}

        def mock_post(url, **kwargs):
            resp = MagicMock(spec=httpx.Response)
            resp.status_code = 200
            resp.headers = {"content-type": "application/json"}
            resp.json = lambda: {
                "data": {"__schema": {"types": [{"name": "Query"}, {"name": "User"}]}}
            }
            return resp

        with patch("httpx.post", side_effect=mock_post):
            score, findings = check._check_graphql("https://example.com", details)
        assert score == 1.0
        assert details["graphql"] is True
        assert details["graphql_types"] == 2

    def test_no_graphql(self):
        check = _make_check()
        details: dict = {}

        with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
            score, findings = check._check_graphql("https://example.com", details)
        assert score == 0.0
        assert details["graphql"] is False


class TestCORS:
    def test_open_cors(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(headers={"access-control-allow-origin": "*"})
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_cors("https://example.com", details)
        assert score == 1.0

    def test_no_cors(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response()
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_cors("https://example.com", details)
        assert score == 0.2
        assert "No CORS" in findings[0]

    def test_restricted_cors(self):
        check = _make_check()
        details: dict = {}
        resp = _mock_response(headers={"access-control-allow-origin": "https://app.example.com"})
        with patch.object(check, "_fetch", return_value=resp):
            score, findings = check._check_cors("https://example.com", details)
        assert score == 0.7


class TestContentNegotiation:
    def test_proper_negotiation(self):
        check = _make_check()
        details: dict = {}

        call_count = 0

        def mock_fetch(url, **kwargs):
            nonlocal call_count
            call_count += 1
            accept = kwargs.get("headers", {}).get("Accept", "")
            if "json" in accept:
                return _mock_response(content_type="application/json")
            return _mock_response(content_type="text/html")

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            score, findings = check._check_content_negotiation("https://example.com", details)
        assert score == 1.0

    def test_no_negotiation(self):
        check = _make_check()
        details: dict = {}
        with patch.object(check, "_fetch", return_value=_mock_response(content_type="text/html")):
            score, findings = check._check_content_negotiation("https://example.com", details)
        assert score == 0.2
