"""Site scoring engine — aggregates individual checks into an overall score."""

from __future__ import annotations


from agent_bench.analysis.models import CheckResult
from agent_bench.analysis.report import AnalysisReport


# Default weights for each check category (sum to 1.0)
DEFAULT_WEIGHTS: dict[str, float] = {
    "api": 0.20,
    "auth": 0.10,
    "docs": 0.15,
    "structure": 0.15,
    "errors": 0.10,
    "cost": 0.15,
    "a11y": 0.15,
}


def _get_builtin_checks() -> dict[str, type]:
    """Load built-in check classes."""
    from agent_bench.analysis.checks.a11y import A11yCheck
    from agent_bench.analysis.checks.api import APICheck
    from agent_bench.analysis.checks.auth import AuthCheck
    from agent_bench.analysis.checks.docs import DocsCheck
    from agent_bench.analysis.checks.errors import ErrorsCheck
    from agent_bench.analysis.checks.cost import CostCheck
    from agent_bench.analysis.checks.structure import StructureCheck

    return {
        "a11y": A11yCheck,
        "api": APICheck,
        "auth": AuthCheck,
        "docs": DocsCheck,
        "structure": StructureCheck,
        "errors": ErrorsCheck,
        "cost": CostCheck,
    }


def _get_plugin_checks() -> dict[str, type]:
    """Discover check plugins via entry points (group: agent_bench.checks)."""
    import sys

    plugins: dict[str, type] = {}

    if sys.version_info >= (3, 12):
        from importlib.metadata import entry_points
        eps = entry_points(group="agent_bench.checks")
    else:
        from importlib.metadata import entry_points
        all_eps = entry_points()
        eps = all_eps.get("agent_bench.checks", [])

    for ep in eps:
        try:
            check_cls = ep.load()
            # Entry point name is the authoritative key (allows overriding builtins)
            plugins[ep.name] = check_cls
        except Exception:
            pass  # Skip broken plugins silently

    return plugins


def _get_check_registry() -> dict[str, type]:
    """Get all checks: built-in + plugins. Plugins override built-ins."""
    registry = _get_builtin_checks()
    registry.update(_get_plugin_checks())
    return registry


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
