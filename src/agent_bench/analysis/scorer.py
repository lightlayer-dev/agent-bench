"""Site scoring engine — aggregates individual checks into an overall score."""

from __future__ import annotations


from agent_bench.analysis.models import CheckResult
from agent_bench.analysis.report import AnalysisReport


# Default weights for each check category (sum to 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "api": 0.25,
    "auth": 0.10,
    "docs": 0.15,
    "structure": 0.20,
    "errors": 0.10,
    "cost": 0.20,
}


def _get_check_registry() -> dict[str, type]:
    """Lazy-load check registry to avoid circular imports."""
    from agent_bench.analysis.checks.api import APICheck
    from agent_bench.analysis.checks.auth import AuthCheck
    from agent_bench.analysis.checks.docs import DocsCheck
    from agent_bench.analysis.checks.errors import ErrorsCheck
    from agent_bench.analysis.checks.cost import CostCheck
    from agent_bench.analysis.checks.structure import StructureCheck

    return {
        "api": APICheck,
        "auth": AuthCheck,
        "docs": DocsCheck,
        "structure": StructureCheck,
        "errors": ErrorsCheck,
        "cost": CostCheck,
    }


class SiteScorer:
    """Runs all configured checks against a URL and produces a scored report."""

    def __init__(self, url: str, checks: list[str] | None = None) -> None:
        self.url = url
        self.check_names = checks or list(DEFAULT_WEIGHTS.keys())

    def run(self) -> AnalysisReport:
        """Execute all checks and return a report."""
        registry = _get_check_registry()
        results: list[CheckResult] = []

        for name in self.check_names:
            check_cls = registry.get(name)
            if check_cls is None:
                continue
            check = check_cls(url=self.url)
            result = check.execute()
            results.append(result)

        overall = self._compute_overall(results)
        return AnalysisReport(url=self.url, overall_score=overall, check_results=results)

    def _compute_overall(self, results: list[CheckResult]) -> float:
        """Weighted average of all check scores."""
        total_weight = 0.0
        weighted_sum = 0.0

        for result in results:
            weight = DEFAULT_WEIGHTS.get(result.name, 0.1)
            weighted_sum += result.score * weight
            total_weight += weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0
