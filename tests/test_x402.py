"""Tests for the x402 payment protocol analysis check."""

import json
from unittest.mock import patch, MagicMock

import httpx

from agent_bench.analysis.checks.x402 import X402Check


def _make_check(url: str = "https://example.com") -> X402Check:
    return X402Check(url=url)


def _mock_response(
    status: int = 200,
    text: str = "",
    content_type: str = "application/json",
    headers: dict | None = None,
) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    h = {"content-type": content_type}
    if headers:
        h.update(headers)
    resp.headers = h
    resp.json = lambda: json.loads(text) if text else {}
    return resp


X402_DISCOVERY = json.dumps(
    {
        "scheme": "exact",
        "network": "base-sepolia",
        "asset": "USDC",
        "facilitator": "https://x402.org/facilitator",
        "version": 1,
    }
)


class TestDiscovery:
    def test_no_x402(self):
        check = _make_check()
        with patch.object(check, "_fetch", return_value=None):
            result = check.execute()
        assert result.score == 0.0
        assert not result.details.get("x402_discovery")

    def test_x402_well_known(self):
        def mock_fetch(url):
            if "/.well-known/x402" in url:
                return _mock_response(text=X402_DISCOVERY)
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            # Also mock the 402 response check
            with patch("httpx.get", return_value=_mock_response(status=404)):
                result = check.execute()

        assert result.details["x402_discovery"]
        assert result.score > 0.3


class TestHTTP402:
    def test_402_with_payment_header(self):
        def mock_fetch(url):
            return None

        check = _make_check()
        resp_402 = _mock_response(
            status=402,
            headers={"payment-required": '{"scheme":"exact","amount":"0.01"}'},
        )

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            with patch("httpx.get", return_value=resp_402):
                result = check.execute()

        assert result.details.get("x402_402_found")
        assert result.details.get("x402_has_payment_header")

    def test_402_without_header(self):
        def mock_fetch(url):
            return None

        check = _make_check()
        resp_402 = _mock_response(status=402)

        with patch.object(check, "_fetch", side_effect=mock_fetch):
            with patch("httpx.get", return_value=resp_402):
                result = check.execute()

        assert result.details.get("x402_402_found")
        assert not result.details.get("x402_has_payment_header")

    def test_no_402_responses(self):
        check = _make_check()
        resp_404 = _mock_response(status=404)

        with patch.object(check, "_fetch", return_value=None):
            with patch("httpx.get", return_value=resp_404):
                result = check.execute()

        assert not result.details.get("x402_402_found")


class TestPaymentSignals:
    def test_payment_in_agents_txt(self):
        agents_txt = "User-agent: *\nAllow: /\nPayment: x402\n"

        def mock_fetch(url):
            if "agents.txt" in url:
                return _mock_response(text=agents_txt, content_type="text/plain")
            return None

        check = _make_check()
        with patch.object(check, "_fetch", side_effect=mock_fetch):
            with patch("httpx.get", return_value=_mock_response(status=404)):
                result = check.execute()

        assert result.details.get("x402_in_agents_txt")
