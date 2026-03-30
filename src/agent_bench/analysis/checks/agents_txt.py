"""Check: agents.txt — machine-readable agent permission manifest.

agents.txt is a proposed standard (like robots.txt for AI agents) that declares
which agents are allowed, what scopes they have, rate limits, and payment info.

See: https://agentprotocols.org/agents-txt
"""

from __future__ import annotations

import httpx

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class AgentsTxtCheck(BaseCheck):
    """Evaluate agents.txt adoption and quality.

    Checks for:
    - /agents.txt or /.well-known/agents.txt
    - Valid structure (agent blocks, permissions, rate limits)
    - Payment/monetisation declarations
    - Contact information for agent developers
    """

    name = "agents_txt"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. Check for agents.txt at standard paths
        score, f = self._check_presence(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. If found, evaluate quality
        if details.get("agents_txt_found"):
            score, f = self._check_quality(details)
            sub_scores.append(score)
            findings.extend(f)
        else:
            sub_scores.append(0.0)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
        return CheckResult(
            name=self.name, score=overall, findings=findings, details=details
        )

    def _fetch(self, url: str) -> httpx.Response | None:
        try:
            return httpx.get(url, follow_redirects=True, timeout=10)
        except httpx.HTTPError:
            return None

    def _check_presence(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        findings = []
        paths = ["/agents.txt", "/.well-known/agents.txt"]

        for path in paths:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200 and len(resp.text.strip()) > 10:
                ct = resp.headers.get("content-type", "")
                # Should be text, not HTML
                if (
                    "html" in ct.lower()
                    and "user-agent:" not in resp.text.lower()[:500]
                ):
                    continue

                details["agents_txt_found"] = True
                details["agents_txt_path"] = path
                details["agents_txt_length"] = len(resp.text)
                details["agents_txt_content"] = resp.text[:2000]
                findings.append(f"agents.txt found at {path} ({len(resp.text)} chars)")
                return 1.0, findings

        details["agents_txt_found"] = False
        findings.append(
            "No agents.txt found — agents have no machine-readable permission manifest"
        )
        return 0.0, findings

    def _check_quality(self, details: dict) -> tuple[float, list[str]]:
        """Evaluate the quality/completeness of agents.txt content."""
        findings = []
        content = details.get("agents_txt_content", "")
        text_lower = content.lower()
        score = 0.0

        # Check for agent blocks (User-agent or Agent directives)
        has_agent_blocks = "user-agent:" in text_lower or "agent:" in text_lower
        if has_agent_blocks:
            score += 0.3
            findings.append("agents.txt contains agent permission blocks")
        else:
            findings.append("agents.txt lacks agent/user-agent blocks")

        # Check for allow/disallow directives
        has_permissions = "allow:" in text_lower or "disallow:" in text_lower
        if has_permissions:
            score += 0.2
            findings.append("agents.txt declares allow/disallow permissions")

        # Check for rate limit info
        has_rate_limits = (
            "rate-limit:" in text_lower
            or "crawl-delay:" in text_lower
            or "request-rate:" in text_lower
        )
        if has_rate_limits:
            score += 0.2
            findings.append("agents.txt includes rate limit information")

        # Check for contact/payment info
        has_contact = "contact:" in text_lower or "email:" in text_lower
        if has_contact:
            score += 0.15
            findings.append("agents.txt includes contact information")

        has_payment = (
            "payment:" in text_lower or "x402:" in text_lower or "monetiz" in text_lower
        )
        if has_payment:
            score += 0.15
            findings.append("agents.txt includes payment/monetisation info")

        details["agents_txt_has_blocks"] = has_agent_blocks
        details["agents_txt_has_permissions"] = has_permissions
        details["agents_txt_has_rate_limits"] = has_rate_limits
        details["agents_txt_has_contact"] = has_contact
        details["agents_txt_has_payment"] = has_payment

        return min(score, 1.0), findings
