"""Tests for trend chart HTML rendering."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from agent_bench.analysis.trend import ScoreSnapshot, SiteTrend, TrendStore
from agent_bench.analysis.trend_chart import (
    _svg_sparkline,
    render_trend_html,
    render_multi_trend_html,
)
from agent_bench.cli import cli


class TestSvgSparkline:
    def test_empty_values(self):
        assert _svg_sparkline([]) == ""

    def test_single_value(self):
        svg = _svg_sparkline([0.5])
        assert "<svg" in svg
        assert "circle" in svg

    def test_multiple_values(self):
        svg = _svg_sparkline([0.2, 0.5, 0.8])
        assert "polyline" in svg
        assert "circle" in svg

    def test_custom_dimensions(self):
        svg = _svg_sparkline([0.3, 0.7], width=200, height=40)
        assert 'width="200"' in svg
        assert 'height="40"' in svg


class TestRenderTrendHtml:
    def _make_trend(self):
        return SiteTrend(
            url="https://example.com",
            snapshots=[
                ScoreSnapshot(timestamp="2026-03-01T00:00:00+00:00", overall_score=0.4, check_scores={"api": 0.3, "docs": 0.5}),
                ScoreSnapshot(timestamp="2026-03-08T00:00:00+00:00", overall_score=0.6, check_scores={"api": 0.5, "docs": 0.7}),
            ],
        )

    def test_contains_url(self):
        html = render_trend_html(self._make_trend())
        assert "https://example.com" in html

    def test_contains_latest_score(self):
        html = render_trend_html(self._make_trend())
        assert "60%" in html

    def test_contains_sparkline(self):
        html = render_trend_html(self._make_trend())
        assert "<svg" in html

    def test_contains_check_names(self):
        html = render_trend_html(self._make_trend())
        assert "api" in html
        assert "docs" in html

    def test_contains_timeline(self):
        html = render_trend_html(self._make_trend())
        assert "2026-03-01" in html
        assert "2026-03-08" in html


class TestRenderMultiTrendHtml:
    def test_empty_store(self, tmp_path):
        store = TrendStore(tmp_path / "empty.json")
        html = render_multi_trend_html(store)
        assert "No trend data" in html

    def test_with_sites(self, tmp_path):
        store = TrendStore(tmp_path / "trends.json")
        store.add("https://a.com", 0.5, {"api": 0.6}, timestamp="2026-03-01T00:00:00+00:00")
        store.add("https://b.com", 0.7, {"api": 0.8}, timestamp="2026-03-01T00:00:00+00:00")
        html = render_multi_trend_html(store)
        assert "https://a.com" in html
        assert "https://b.com" in html
        assert "2 sites tracked" in html


class TestTrendCliHtml:
    def test_trend_html_output(self, tmp_path):
        store_path = tmp_path / "trends.json"
        store = TrendStore(store_path)
        store.add("https://example.com", 0.5, {"api": 0.6}, timestamp="2026-03-01T00:00:00+00:00")
        store.add("https://example.com", 0.7, {"api": 0.8}, timestamp="2026-03-08T00:00:00+00:00")

        out = tmp_path / "trend.html"
        runner = CliRunner()
        result = runner.invoke(cli, ["trend", "https://example.com", "--store", str(store_path), "--format", "html", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        html = out.read_text()
        assert "https://example.com" in html

    def test_trend_html_all(self, tmp_path):
        store_path = tmp_path / "trends.json"
        store = TrendStore(store_path)
        store.add("https://a.com", 0.5, {}, timestamp="2026-03-01T00:00:00+00:00")

        out = tmp_path / "all.html"
        runner = CliRunner()
        result = runner.invoke(cli, ["trend", "--all", "--store", str(store_path), "--format", "html", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()
