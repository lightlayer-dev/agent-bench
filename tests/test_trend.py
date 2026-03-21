"""Tests for trend tracking."""

from __future__ import annotations


from click.testing import CliRunner

from agent_bench.analysis.trend import ScoreSnapshot, SiteTrend, TrendStore, render_trend_table
from agent_bench.cli import cli


class TestScoreSnapshot:
    def test_dt_parsing(self):
        s = ScoreSnapshot(timestamp="2026-03-15T08:00:00+00:00", overall_score=0.5)
        assert s.dt.year == 2026
        assert s.dt.month == 3


class TestSiteTrend:
    def _make_trend(self, scores):
        snaps = [
            ScoreSnapshot(timestamp=f"2026-03-{10+i:02d}T00:00:00+00:00", overall_score=s, check_scores={"api": s})
            for i, s in enumerate(scores)
        ]
        return SiteTrend(url="https://example.com", snapshots=snaps)

    def test_single_snapshot_no_delta(self):
        t = self._make_trend([0.5])
        assert t.delta is None
        assert t.direction == "—"

    def test_improving(self):
        t = self._make_trend([0.3, 0.5, 0.7])
        assert t.delta > 0
        assert t.direction == "▲"

    def test_declining(self):
        t = self._make_trend([0.7, 0.5, 0.3])
        assert t.delta < 0
        assert t.direction == "▼"

    def test_stable(self):
        t = self._make_trend([0.5, 0.505])
        assert t.direction == "="

    def test_check_delta(self):
        t = self._make_trend([0.3, 0.7])
        assert abs(t.check_delta("api") - 0.4) < 0.001

    def test_latest_oldest(self):
        t = self._make_trend([0.3, 0.7])
        assert t.oldest.overall_score == 0.3
        assert t.latest.overall_score == 0.7

    def test_empty(self):
        t = SiteTrend(url="https://empty.com")
        assert t.latest is None
        assert t.oldest is None
        assert t.delta is None


class TestTrendStore:
    def test_add_and_retrieve(self, tmp_path):
        store = TrendStore(tmp_path / "history.json")
        store.add("https://example.com", 0.5, {"api": 0.6}, timestamp="2026-03-15T00:00:00+00:00")
        store.add("https://example.com", 0.7, {"api": 0.8}, timestamp="2026-03-16T00:00:00+00:00")

        trend = store.get_trend("https://example.com")
        assert len(trend.snapshots) == 2
        assert trend.direction == "▲"

    def test_persistence(self, tmp_path):
        path = tmp_path / "history.json"
        store1 = TrendStore(path)
        store1.add("https://x.com", 0.4, {}, timestamp="2026-03-15T00:00:00+00:00")

        store2 = TrendStore(path)
        assert len(store2.get_trend("https://x.com").snapshots) == 1

    def test_add_from_result(self, tmp_path):
        store = TrendStore(tmp_path / "h.json")
        result = {
            "url": "https://test.com",
            "timestamp": "2026-03-15T00:00:00+00:00",
            "overall_score": 0.6,
            "checks": [{"name": "api", "score": 0.7}],
        }
        store.add_from_result(result)
        trend = store.get_trend("https://test.com")
        assert len(trend.snapshots) == 1
        assert trend.snapshots[0].check_scores["api"] == 0.7

    def test_all_urls(self, tmp_path):
        store = TrendStore(tmp_path / "h.json")
        store.add("https://b.com", 0.5, {})
        store.add("https://a.com", 0.5, {})
        assert store.all_urls() == ["https://a.com", "https://b.com"]

    def test_unknown_url_empty(self, tmp_path):
        store = TrendStore(tmp_path / "h.json")
        trend = store.get_trend("https://nope.com")
        assert len(trend.snapshots) == 0


class TestRenderTrendTable:
    def test_renders_snapshots(self):
        snaps = [
            ScoreSnapshot(timestamp="2026-03-15T00:00:00+00:00", overall_score=0.4),
            ScoreSnapshot(timestamp="2026-03-16T00:00:00+00:00", overall_score=0.6),
        ]
        trend = SiteTrend(url="https://example.com", snapshots=snaps)
        text = render_trend_table(trend)
        assert "example.com" in text
        assert "▲" in text
        assert "+20%" in text

    def test_empty_trend(self):
        trend = SiteTrend(url="https://empty.com")
        text = render_trend_table(trend)
        assert "No history" in text


class TestTrendCLI:
    def test_trend_no_args_fails(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["trend"])
        assert result.exit_code != 0

    def test_trend_unknown_url(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["trend", "https://nope.com", "--store", str(tmp_path / "h.json")])
        assert result.exit_code == 0
        assert "No history" in result.output

    def test_trend_all_empty(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(cli, ["trend", "--all", "--store", str(tmp_path / "h.json")])
        assert result.exit_code == 0
        assert "No trend history" in result.output

    def test_trend_all_with_data(self, tmp_path):
        store_path = tmp_path / "h.json"
        store = TrendStore(store_path)
        store.add("https://a.com", 0.5, {}, timestamp="2026-03-15T00:00:00+00:00")
        runner = CliRunner()
        result = runner.invoke(cli, ["trend", "--all", "--store", str(store_path)])
        assert result.exit_code == 0
        assert "a.com" in result.output
