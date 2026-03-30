"""Tests for CI integration features — threshold, quiet mode."""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from agent_bench.cli import cli
from agent_bench.analysis.models import CheckResult
from agent_bench.analysis.report import AnalysisReport

SCORER_PATH = "agent_bench.analysis.scorer.SiteScorer"


def _mock_report(score: float) -> AnalysisReport:
    return AnalysisReport(
        url="https://example.com",
        overall_score=score,
        check_results=[
            CheckResult(
                name="api", score=score, max_score=1.0, details={}, findings=["test"]
            ),
        ],
    )


@pytest.fixture
def runner():
    return CliRunner()


class TestThreshold:
    """Test --threshold flag for CI pipeline gating."""

    @patch(SCORER_PATH)
    def test_above_threshold_exits_0(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.65)
        result = runner.invoke(
            cli, ["analyze", "https://example.com", "--threshold", "0.5"]
        )
        assert result.exit_code == 0
        assert "PASS" in result.output

    @patch(SCORER_PATH)
    def test_below_threshold_exits_1(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.30)
        result = runner.invoke(
            cli, ["analyze", "https://example.com", "--threshold", "0.5"]
        )
        assert result.exit_code == 1
        assert "FAIL" in result.output

    @patch(SCORER_PATH)
    def test_exact_threshold_passes(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.50)
        result = runner.invoke(
            cli, ["analyze", "https://example.com", "--threshold", "0.5"]
        )
        assert result.exit_code == 0

    @patch(SCORER_PATH)
    def test_no_threshold_always_exits_0(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.10)
        result = runner.invoke(cli, ["analyze", "https://example.com"])
        assert result.exit_code == 0

    @patch(SCORER_PATH)
    def test_threshold_with_output(self, mock_scorer_cls, runner, tmp_path):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.65)
        out = str(tmp_path / "result.json")
        result = runner.invoke(
            cli,
            ["analyze", "https://example.com", "--threshold", "0.5", "--output", out],
        )
        assert result.exit_code == 0
        data = json.loads((tmp_path / "result.json").read_text())
        assert data["overall_score"] == 0.65


class TestQuietMode:
    """Test --quiet flag for CI-friendly output."""

    @patch(SCORER_PATH)
    def test_quiet_suppresses_output(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.65)
        result = runner.invoke(cli, ["analyze", "https://example.com", "--quiet"])
        assert result.exit_code == 0
        assert "Analyzing" not in result.output

    @patch(SCORER_PATH)
    def test_quiet_with_threshold_still_shows_fail(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.30)
        result = runner.invoke(
            cli, ["analyze", "https://example.com", "--quiet", "--threshold", "0.5"]
        )
        assert result.exit_code == 1
        assert "FAIL" in result.output

    @patch(SCORER_PATH)
    def test_quiet_with_output_saves_file(self, mock_scorer_cls, runner, tmp_path):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.50)
        out = str(tmp_path / "r.json")
        result = runner.invoke(
            cli, ["analyze", "https://example.com", "--quiet", "--output", out]
        )
        assert result.exit_code == 0
        assert (tmp_path / "r.json").exists()

    @patch(SCORER_PATH)
    def test_quiet_pass_suppresses_pass_message(self, mock_scorer_cls, runner):
        mock_scorer_cls.return_value.run.return_value = _mock_report(0.65)
        result = runner.invoke(
            cli, ["analyze", "https://example.com", "--quiet", "--threshold", "0.5"]
        )
        assert result.exit_code == 0
        assert "PASS" not in result.output
