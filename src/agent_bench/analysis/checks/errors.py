"""Check: Error handling and rate limiting quality."""

from __future__ import annotations

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class ErrorsCheck(BaseCheck):
    """Evaluate error handling quality for agents.

    Checks for:
    - Structured error responses (JSON with error codes)
    - Rate limit headers (X-RateLimit-*, Retry-After)
    - Meaningful HTTP status codes
    - Error message clarity (actionable vs generic)
    - Graceful degradation on bad input
    """

    name = "errors"

    def execute(self) -> CheckResult:
        score = 0.0
        findings: list[str] = []
        details: dict[str, object] = {}

        # TODO: Send malformed request, check error response format
        # TODO: Check for rate limit headers on normal responses
        # TODO: Hit a 404 and evaluate the error page/response
        # TODO: Check if errors are JSON vs HTML
        # TODO: Evaluate error message actionability

        return CheckResult(name=self.name, score=score, findings=findings, details=details)
