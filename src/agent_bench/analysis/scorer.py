"""Site scoring engine — aggregates individual checks into an overall score."""

from __future__ import annotations

from dataclasses import dataclass, field

from agent_bench.analysis.checks.api import APICheck
from agent_bench.analysis.checks.auth import AuthCheck
from agent_bench.analysis.checks.docs import DocsCheck
from agent_bench.analysis.checks.errors import ErrorsCheck
from agent_bench.analysis.checks.structure import StructureCheck
from agent_bench.analysis.report import AnalysisReport


# Map of check name -> check class
CHECK_REGISTRY: dict[str, type] = {
    "api": APICheck,
    "auth": AuthCheck,
    "docs": DocsCheck,
    "structure": StructureCheck,
    "errors": ErrorsCheck,
}

# Default weights for each check category (sum to 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "api": 0.30,
    "auth": 0.15,
    "docs": 0.20,
    "structure": 0.20,
    "errors": 0.15,
}


@dataclass
class CheckResult:
    """Result from a single check category."""

    name: str
    score: float  # 0.0 - 1.0
    max_score: float = 1.0
    details: dict[str, object] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)


class SiteScorer:
    """Runs all configured checks against a URL and produces a scored report."""

    def __init__(self, url: str, checks: list[str] | None = None) -> None:
        self.url = url
        self.check_names = checks or list(CHECK_REGISTRY.keys())

    def run(self) -> AnalysisReport:
        """Execute all checks and return a report."""
        results: list[CheckResult] = []

        for name in self.check_names:
            check_cls = CHECK_REGISTRY.get(name)
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
