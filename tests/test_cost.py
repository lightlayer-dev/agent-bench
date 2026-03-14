"""Tests for cost analysis check."""

import httpx
import pytest

from agent_bench.analysis.checks.cost import CostCheck, CHARS_PER_TOKEN


def _mock_response(html: str):
    return httpx.Response(200, text=html, request=httpx.Request("GET", "https://example.com"))


class TestPageTokenCount:
    def test_small_page_efficient(self, monkeypatch):
        html = "<html><body><p>Hello world</p></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert result.score >= 0.8
        assert any("efficient" in f for f in result.findings)

    def test_huge_page_expensive(self, monkeypatch):
        # 100k chars = ~25k tokens
        html = "<html><body>" + "<p>x</p>" * 15000 + "</body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert any("expensive" in f or "moderate" in f for f in result.findings)


class TestSignalToNoise:
    def test_high_signal(self, monkeypatch):
        html = "<html><body><article><p>Useful content here about AI agents.</p></article></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert result.score >= 0.7

    def test_low_signal_script_heavy(self, monkeypatch):
        scripts = "<script>" + "var x = 1;\n" * 500 + "</script>"
        html = f"<html><body>{scripts}<p>tiny content</p></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert any("noise" in f or "bloat" in f for f in result.findings)


class TestInlineBloat:
    def test_no_inline(self, monkeypatch):
        html = "<html><body><p>Clean page</p></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert any("reasonable" in f for f in result.findings)

    def test_heavy_inline_styles(self, monkeypatch):
        style = "<style>" + ".cls { color: red; margin: 0; padding: 0; }\n" * 200 + "</style>"
        html = f"<html><head>{style}</head><body><p>x</p></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        # Should detect bloat
        assert any("bloat" in f.lower() or "scripts/styles" in f for f in result.findings)


class TestDOMDepth:
    def test_shallow_dom(self, monkeypatch):
        html = "<html><body><main><p>Hello</p></main></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert any("clean structure" in f for f in result.findings)

    def test_deep_dom(self, monkeypatch):
        inner = "<p>deep</p>"
        for _ in range(30):
            inner = f"<div>{inner}</div>"
        html = f"<html><body>{inner}</body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert any("deeply nested" in f for f in result.findings)


class TestClassBloat:
    def test_utility_class_heavy(self, monkeypatch):
        # Simulate Tailwind-style classes
        divs = ''.join(
            f'<div class="flex items-center justify-between px-4 py-2 bg-gray-100 text-sm font-medium rounded-lg shadow-md hover:bg-gray-200 transition-colors duration-200">item {i}</div>'
            for i in range(100)
        )
        html = f"<html><body>{divs}</body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        assert any("class" in f.lower() for f in result.findings)

    def test_no_classes(self, monkeypatch):
        html = "<html><body><p>Simple page</p></body></html>"
        monkeypatch.setattr(httpx, "get", lambda *a, **kw: _mock_response(html))
        result = CostCheck("https://example.com").execute()
        # Should not mention class bloat
        class_findings = [f for f in result.findings if "class" in f.lower()]
        assert len(class_findings) == 0


class TestFetchFailure:
    def test_network_error(self, monkeypatch):
        def fail(*a, **kw):
            raise httpx.ConnectError("Connection refused")
        monkeypatch.setattr(httpx, "get", fail)
        result = CostCheck("https://example.com").execute()
        assert result.score == 0.0
        assert any("Failed" in f for f in result.findings)
