"""Check: API surface availability and quality."""

from __future__ import annotations

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class APICheck(BaseCheck):
    """Evaluate API availability and quality.

    Checks for:
    - REST API endpoints (common paths like /api, /api/v1, etc.)
    - OpenAPI/Swagger spec availability
    - GraphQL endpoint
    - Response format (JSON vs HTML)
    - Pagination support
    - CORS headers
    """

    name = "api"

    def execute(self) -> CheckResult:
        score = 0.0
        findings: list[str] = []
        details: dict[str, object] = {}

        # TODO: Probe common API paths
        # TODO: Check for OpenAPI spec at /openapi.json, /swagger.json, /api-docs
        # TODO: Check for GraphQL at /graphql
        # TODO: Evaluate response structure quality
        # TODO: Check CORS headers
        # TODO: Check pagination patterns (Link header, cursor, offset)

        return CheckResult(name=self.name, score=score, findings=findings, details=details)
