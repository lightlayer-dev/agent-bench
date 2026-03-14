"""Check: Machine-readable documentation quality."""

from __future__ import annotations

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.scorer import CheckResult


class DocsCheck(BaseCheck):
    """Evaluate documentation quality for agent consumption.

    Checks for:
    - OpenAPI/Swagger specifications
    - JSON Schema definitions
    - robots.txt and sitemap.xml
    - Structured data (JSON-LD, microdata)
    - API documentation pages
    - Example requests/responses in docs
    """

    name = "docs"

    def execute(self) -> CheckResult:
        score = 0.0
        findings: list[str] = []
        details: dict[str, object] = {}

        # TODO: Fetch and parse robots.txt
        # TODO: Check for sitemap.xml
        # TODO: Look for structured data in HTML (JSON-LD, microdata)
        # TODO: Evaluate OpenAPI spec completeness if found
        # TODO: Check for llms.txt (emerging standard)

        return CheckResult(name=self.name, score=score, findings=findings, details=details)
