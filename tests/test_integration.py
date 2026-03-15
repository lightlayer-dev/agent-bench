"""Integration tests — run the full analyzer against real sites.

These tests hit the network and are marked with @pytest.mark.integration.
Run with: pytest tests/test_integration.py -v -m integration
Skip in CI with: pytest -m "not integration"
"""

import pytest

from agent_bench.analysis.scorer import SiteScorer
from agent_bench.analysis.report import AnalysisReport


@pytest.mark.integration
class TestFullAnalysis:
    """End-to-end tests against real websites."""

    def test_analyze_httpbin(self):
        """httpbin.org — a simple API testing site."""
        scorer = SiteScorer(url="https://httpbin.org")
        report = scorer.run()

        assert isinstance(report, AnalysisReport)
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.check_results) == 8

        # Every check should have findings
        for result in report.check_results:
            assert result.name in ("a11y", "api", "auth", "docs", "structure", "errors", "cost", "performance")
            assert 0.0 <= result.score <= 1.0
            assert len(result.findings) > 0

    def test_analyze_jsonplaceholder(self):
        """jsonplaceholder.typicode.com — a fake REST API."""
        scorer = SiteScorer(url="https://jsonplaceholder.typicode.com")
        report = scorer.run()

        assert isinstance(report, AnalysisReport)
        assert 0.0 <= report.overall_score <= 1.0
        assert len(report.check_results) == 8

    def test_analyze_single_check(self):
        """Run only the docs check."""
        scorer = SiteScorer(url="https://httpbin.org", checks=["docs"])
        report = scorer.run()

        assert len(report.check_results) == 1
        assert report.check_results[0].name == "docs"

    def test_report_formats(self):
        """Verify all report formats render without error."""
        scorer = SiteScorer(url="https://httpbin.org")
        report = scorer.run()

        table = report.render("table")
        assert "Agent-Readiness Score" in table
        assert len(table) > 100

        md = report.render("markdown")
        assert "# Agent-Readiness Report" in md

        json_str = report.render("json")
        import json
        data = json.loads(json_str)
        assert "overall_score" in data
        assert len(data["checks"]) == 8

    def test_cli_analyze(self):
        """Test the CLI analyze command."""
        from click.testing import CliRunner
        from agent_bench.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "https://httpbin.org"])
        assert result.exit_code == 0
        assert "Analyzing" in result.output
