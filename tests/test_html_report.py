"""Tests for HTML report generation."""

from agent_bench.analysis.models import CheckResult
from agent_bench.analysis.report import AnalysisReport
from agent_bench.analysis.html_report import (
    render_html_report,
    _score_color,
    _score_label,
)


class TestScoreHelpers:
    def test_score_color_green(self):
        assert _score_color(0.8) == "#4ade80"

    def test_score_color_amber(self):
        assert _score_color(0.5) == "#fbbf24"

    def test_score_color_red(self):
        assert _score_color(0.2) == "#f87171"

    def test_score_label(self):
        assert _score_label(0.9) == "Good"
        assert _score_label(0.5) == "Moderate"
        assert _score_label(0.1) == "Poor"


class TestHTMLReport:
    def test_renders_valid_html(self):
        report = AnalysisReport(
            url="https://example.com",
            overall_score=0.65,
            check_results=[
                CheckResult(name="api", score=0.8, findings=["Found 3 API endpoints"]),
                CheckResult(name="docs", score=0.4, findings=["No sitemap"]),
                CheckResult(
                    name="structure", score=0.7, findings=["Good semantic HTML"]
                ),
                CheckResult(name="auth", score=0.9, findings=["No CAPTCHA"]),
                CheckResult(name="errors", score=0.3, findings=["HTML 404 page"]),
            ],
        )
        html = render_html_report(report)

        assert "<!DOCTYPE html>" in html
        assert "https://example.com" in html
        assert "65%" in html
        assert "Agent-Readiness Report" in html
        assert "agent-bench" in html

        # All checks present
        assert "api" in html.lower()
        assert "docs" in html.lower()
        assert "structure" in html.lower()
        assert "auth" in html.lower()
        assert "errors" in html.lower()

        # Findings present
        assert "Found 3 API endpoints" in html
        assert "No sitemap" in html

    def test_report_render_html_format(self):
        report = AnalysisReport(
            url="https://test.com",
            overall_score=0.5,
            check_results=[
                CheckResult(name="api", score=0.5, findings=["test"]),
            ],
        )
        html = report.render("html")
        assert "<!DOCTYPE html>" in html
        assert "test.com" in html

    def test_zero_score(self):
        report = AnalysisReport(
            url="https://bad.com", overall_score=0.0, check_results=[]
        )
        html = render_html_report(report)
        assert "0%" in html
        assert "Poor" in html

    def test_perfect_score(self):
        report = AnalysisReport(
            url="https://good.com", overall_score=1.0, check_results=[]
        )
        html = render_html_report(report)
        assert "100%" in html
        assert "Good" in html
