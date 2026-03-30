"""Tests for the site scoring engine."""

from agent_bench.analysis.models import CheckResult
from agent_bench.analysis.scorer import SiteScorer, DEFAULT_WEIGHTS


def test_check_result_defaults():
    result = CheckResult(name="test", score=0.75)
    assert result.score == 0.75
    assert result.findings == []
    assert result.details == {}


def test_compute_overall_weighted():
    scorer = SiteScorer(url="https://example.com")
    results = [
        CheckResult(name="api", score=0.8),
        CheckResult(name="auth", score=0.6),
        CheckResult(name="docs", score=0.9),
        CheckResult(name="structure", score=0.7),
        CheckResult(name="errors", score=0.5),
    ]
    overall = scorer._compute_overall(results)

    # Manually compute expected
    expected = sum(r.score * DEFAULT_WEIGHTS[r.name] for r in results) / sum(
        DEFAULT_WEIGHTS[r.name] for r in results
    )

    assert abs(overall - expected) < 0.001


def test_compute_overall_empty():
    scorer = SiteScorer(url="https://example.com")
    assert scorer._compute_overall([]) == 0.0
