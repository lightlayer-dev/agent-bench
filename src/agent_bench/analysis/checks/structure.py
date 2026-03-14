"""Check: HTML structure and navigability for agents."""

from __future__ import annotations

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.scorer import CheckResult


class StructureCheck(BaseCheck):
    """Evaluate HTML structure and navigability.

    Checks for:
    - Semantic HTML elements (nav, main, article, section)
    - ARIA labels and roles
    - Form labels and input names
    - Predictable URL patterns
    - Stable CSS selectors / data-testid attributes
    - Client-side rendering vs server-side (SSR is more agent-friendly)
    """

    name = "structure"

    def execute(self) -> CheckResult:
        score = 0.0
        findings: list[str] = []
        details: dict[str, object] = {}

        # TODO: Fetch page HTML and parse with BeautifulSoup
        # TODO: Count semantic vs div-soup ratio
        # TODO: Check for ARIA labels on interactive elements
        # TODO: Evaluate form accessibility (labels, names, types)
        # TODO: Check for data-testid or stable selector attributes
        # TODO: Detect SPA vs SSR (check if content exists without JS)

        return CheckResult(name=self.name, score=score, findings=findings, details=details)
