"""Tests for results comparison."""

import json
from pathlib import Path

import pytest

from agent_bench.results.compare import (
    AnalysisComparison,
    Comparison,
    ComparisonRow,
    ScoreDelta,
    compare_analyses,
    compare_runs,
)


class TestScoreDelta:
    def test_positive_delta(self):
        d = ScoreDelta(check="api", before=0.3, after=0.6)
        assert d.delta == pytest.approx(0.3)
        assert d.direction == "▲"

    def test_negative_delta(self):
        d = ScoreDelta(check="docs", before=0.8, after=0.5)
        assert d.delta == pytest.approx(-0.3)
        assert d.direction == "▼"

    def test_no_change(self):
        d = ScoreDelta(check="auth", before=0.5, after=0.5)
        assert d.delta == pytest.approx(0.0)
        assert d.direction == "="

    def test_tiny_change_treated_as_equal(self):
        d = ScoreDelta(check="cost", before=0.5, after=0.504)
        assert d.direction == "="


class TestAnalysisComparison:
    def _make_result(self, url, score, checks):
        return {
            "url": url,
            "overall_score": score,
            "checks": [{"name": n, "score": s} for n, s in checks.items()],
        }

    def test_compare_analyses(self, tmp_path):
        before = self._make_result("https://example.com", 0.38, {
            "api": 0.3, "docs": 0.4, "structure": 0.5, "auth": 0.2, "errors": 0.4, "cost": 0.5,
        })
        after = self._make_result("https://example.com", 0.65, {
            "api": 0.6, "docs": 0.7, "structure": 0.6, "auth": 0.5, "errors": 0.7, "cost": 0.8,
        })
        bf = tmp_path / "before.json"
        af = tmp_path / "after.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        comp = compare_analyses(bf, af)
        assert comp.url == "https://example.com"
        assert comp.before_score == 0.38
        assert comp.after_score == 0.65
        assert comp.overall_delta == pytest.approx(0.27)
        assert comp.overall_direction == "▲"
        assert len(comp.deltas) == 6

    def test_render_table(self, tmp_path):
        before = self._make_result("https://x.com", 0.30, {"api": 0.2, "docs": 0.4})
        after = self._make_result("https://x.com", 0.50, {"api": 0.5, "docs": 0.5})
        bf = tmp_path / "b.json"
        af = tmp_path / "a.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        comp = compare_analyses(bf, af)
        table = comp.render("table")
        assert "Score Comparison" in table
        assert "▲" in table
        assert "api" in table

    def test_render_markdown(self, tmp_path):
        before = self._make_result("https://x.com", 0.30, {"api": 0.2})
        after = self._make_result("https://x.com", 0.50, {"api": 0.5})
        bf = tmp_path / "b.json"
        af = tmp_path / "a.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        comp = compare_analyses(bf, af)
        md = comp.render("markdown")
        assert "## Score Comparison" in md
        assert "| api |" in md

    def test_render_json(self, tmp_path):
        before = self._make_result("https://x.com", 0.30, {"api": 0.2})
        after = self._make_result("https://x.com", 0.50, {"api": 0.5})
        bf = tmp_path / "b.json"
        af = tmp_path / "a.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        comp = compare_analyses(bf, af)
        data = json.loads(comp.render("json"))
        assert data["overall_delta"] == pytest.approx(0.20)
        assert len(data["checks"]) == 1

    def test_new_check_in_after(self, tmp_path):
        before = self._make_result("https://x.com", 0.30, {"api": 0.3})
        after = self._make_result("https://x.com", 0.50, {"api": 0.5, "cost": 0.7})
        bf = tmp_path / "b.json"
        af = tmp_path / "a.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        comp = compare_analyses(bf, af)
        assert len(comp.deltas) == 2
        cost_delta = [d for d in comp.deltas if d.check == "cost"][0]
        assert cost_delta.before == 0.0
        assert cost_delta.after == 0.7

    def test_regression_detected(self, tmp_path):
        before = self._make_result("https://x.com", 0.60, {"api": 0.8})
        after = self._make_result("https://x.com", 0.40, {"api": 0.4})
        bf = tmp_path / "b.json"
        af = tmp_path / "a.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        comp = compare_analyses(bf, af)
        assert comp.overall_direction == "▼"
        assert comp.deltas[0].direction == "▼"


class TestCompareRuns:
    def test_compare_two_runs(self, tmp_path):
        run1 = {
            "results": [
                {"task": "login", "model": "gpt-4o", "adapter": "browser-use",
                 "success_rate": 0.6, "avg_steps": 5, "avg_time": 10.0, "avg_cost": 0.05}
            ]
        }
        run2 = {
            "results": [
                {"task": "login", "model": "claude-opus", "adapter": "browser-use",
                 "success_rate": 0.8, "avg_steps": 3, "avg_time": 8.0, "avg_cost": 0.08}
            ]
        }
        f1 = tmp_path / "r1.json"
        f2 = tmp_path / "r2.json"
        f1.write_text(json.dumps(run1))
        f2.write_text(json.dumps(run2))

        comp = compare_runs([f1, f2])
        assert len(comp.rows) == 2
        # Sorted by task then success rate desc
        assert comp.rows[0].success_rate == 0.8

    def test_render_formats(self):
        comp = Comparison(rows=[
            ComparisonRow("login", "gpt-4o", "browser-use", 0.8, 3.0, 8.0, 0.05),
        ])
        assert "login" in comp.render("table")
        assert "| login |" in comp.render("markdown")
        data = json.loads(comp.render("json"))
        assert len(data) == 1


class TestCompareCLI:
    def test_compare_analysis_cli(self, tmp_path):
        from click.testing import CliRunner
        from agent_bench.cli import cli

        before = {"url": "https://x.com", "overall_score": 0.3, "checks": [{"name": "api", "score": 0.3}]}
        after = {"url": "https://x.com", "overall_score": 0.6, "checks": [{"name": "api", "score": 0.6}]}
        bf = tmp_path / "b.json"
        af = tmp_path / "a.json"
        bf.write_text(json.dumps(before))
        af.write_text(json.dumps(after))

        runner = CliRunner()
        result = runner.invoke(cli, ["compare", "--before", str(bf), "--after", str(af)])
        assert result.exit_code == 0
        assert "Score Comparison" in result.output

    def test_compare_no_args(self):
        from click.testing import CliRunner
        from agent_bench.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["compare"])
        assert result.exit_code == 0
        assert "--before/--after" in result.output or "--runs" in result.output
