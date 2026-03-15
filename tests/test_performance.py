"""Tests for the performance check."""

from __future__ import annotations

from unittest.mock import MagicMock, patch, PropertyMock
import time

import pytest

from agent_bench.analysis.checks.performance import PerformanceCheck


def _mock_response(html: str, size_kb: float = 50, encoding: str = "gzip", redirects: int = 0):
    resp = MagicMock()
    resp.text = html
    resp.content = b"x" * int(size_kb * 1024)
    resp.headers = {"content-encoding": encoding} if encoding else {}
    resp.history = [MagicMock(url=f"http://r{i}.com") for i in range(redirects)]
    resp.status_code = 200
    return resp


def _run_check(html: str = "<html><body>Hello</body></html>", **kwargs):
    resp = _mock_response(html, **kwargs)

    def fake_get(*args, **kw):
        return resp

    with patch("agent_bench.analysis.checks.performance.httpx.get", side_effect=fake_get):
        with patch("agent_bench.analysis.checks.performance.time.monotonic", side_effect=[0.0, 0.3]):
            check = PerformanceCheck(url="http://example.com")
            result = check.execute()
            return {"score": result.score, "findings": result.findings, "details": result.details}


class TestResponseTime:
    def test_fast_response(self):
        r = _run_check()
        # 300ms is fast
        assert r["details"]["response_time_ms"] == 300.0
        assert any("Fast" in f for f in r["findings"])

    def test_slow_response(self):
        resp = _mock_response("<html></html>")
        with patch("agent_bench.analysis.checks.performance.httpx.get", return_value=resp):
            with patch("agent_bench.analysis.checks.performance.time.monotonic", side_effect=[0.0, 4.0]):
                check = PerformanceCheck(url="http://example.com")
                result = check.execute()
                assert result.details["response_time_ms"] == 4000.0
                assert any("Slow" in f for f in result.findings)


class TestPayloadSize:
    def test_small_payload(self):
        r = _run_check(size_kb=50)
        assert r["details"]["payload_size_kb"] == 50.0
        assert any("Compact" in f for f in r["findings"])

    def test_large_payload(self):
        r = _run_check(size_kb=1500)
        assert any("Large" in f for f in r["findings"])


class TestRedirects:
    def test_no_redirects(self):
        r = _run_check(redirects=0)
        assert r["details"]["redirect_count"] == 0
        assert any("No redirects" in f for f in r["findings"])

    def test_many_redirects(self):
        r = _run_check(redirects=5)
        assert r["details"]["redirect_count"] == 5
        assert any("5 redirects" in f for f in r["findings"])


class TestResources:
    def test_lean_page(self):
        html = "<html><body><p>Simple</p></body></html>"
        r = _run_check(html=html)
        assert r["details"]["script_count"] == 0
        assert any("Lean" in f for f in r["findings"])

    def test_heavy_scripts(self):
        scripts = ''.join(f'<script src="s{i}.js"></script>' for i in range(25))
        html = f"<html><body>{scripts}</body></html>"
        r = _run_check(html=html)
        assert r["details"]["script_count"] == 25
        assert any("heavy JS" in f.lower() or "Resource heavy" in f for f in r["findings"])


class TestCompression:
    def test_gzip(self):
        r = _run_check(encoding="gzip")
        assert r["details"]["content_encoding"] == "gzip"
        assert any("Compression enabled" in f for f in r["findings"])

    def test_no_compression(self):
        r = _run_check(encoding="")
        assert r["details"]["content_encoding"] == "none"
        assert any("No compression" in f for f in r["findings"])

    def test_brotli(self):
        r = _run_check(encoding="br")
        assert r["details"]["content_encoding"] == "br"


class TestOverall:
    def test_good_performance(self):
        r = _run_check(size_kb=30, encoding="gzip", redirects=0)
        assert r["score"] >= 0.7

    def test_poor_performance(self):
        scripts = ''.join(f'<script src="s{i}.js"></script>' for i in range(25))
        html = f"<html><body>{scripts}</body></html>"
        r = _run_check(html=html, size_kb=1500, encoding="", redirects=5)
        assert r["score"] < 0.5
