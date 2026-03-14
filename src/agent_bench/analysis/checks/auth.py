"""Check: Authentication complexity for agents."""

from __future__ import annotations

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class AuthCheck(BaseCheck):
    """Evaluate authentication complexity.

    Checks for:
    - API key authentication (simplest for agents)
    - OAuth 2.0 flows (client_credentials vs authorization_code)
    - Session/cookie-based auth
    - CAPTCHA presence
    - MFA requirements
    - Token refresh mechanisms

    Lower complexity = higher score (easier for agents).
    """

    name = "auth"

    def execute(self) -> CheckResult:
        score = 0.0
        findings: list[str] = []
        details: dict[str, object] = {}

        # TODO: Check for API key auth options
        # TODO: Detect OAuth endpoints (/.well-known/openid-configuration)
        # TODO: Check for CAPTCHA on login/signup
        # TODO: Evaluate cookie/session requirements
        # TODO: Check for bot-detection mechanisms (Cloudflare, etc.)

        return CheckResult(name=self.name, score=score, findings=findings, details=details)
