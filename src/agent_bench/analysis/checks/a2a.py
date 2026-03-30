"""Check: A2A Agent Card — Google's Agent-to-Agent protocol discovery.

The A2A protocol (https://google.github.io/A2A/) defines a standard
agent card at /.well-known/agent.json that declares agent capabilities,
supported protocols, authentication requirements, and service endpoints.

This is essential for agent-to-agent interoperability — without it, agents
can't discover what other agents (or agent-ready services) can do.
"""

from __future__ import annotations

import json

import httpx

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class A2ACheck(BaseCheck):
    """Evaluate A2A Agent Card adoption and quality.

    Checks for:
    - /.well-known/agent.json presence
    - Valid JSON structure with required fields
    - Capability declarations (skills, protocols)
    - Authentication requirements
    - Service endpoint declarations
    """

    name = "a2a"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. Check for agent card
        score, f = self._check_presence(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. If found, evaluate quality
        if details.get("a2a_found"):
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
            return httpx.get(
                url,
                follow_redirects=True,
                timeout=10,
                headers={"Accept": "application/json"},
            )
        except httpx.HTTPError:
            return None

    def _check_presence(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        findings = []
        paths = ["/.well-known/agent.json", "/.well-known/agent-card.json"]

        for path in paths:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and len(data) > 0:
                        details["a2a_found"] = True
                        details["a2a_path"] = path
                        details["a2a_data"] = data
                        findings.append(f"A2A Agent Card found at {path}")
                        return 1.0, findings
                except (json.JSONDecodeError, ValueError):
                    pass

        details["a2a_found"] = False
        findings.append(
            "No A2A Agent Card found (/.well-known/agent.json) — "
            "agents can't discover this service's capabilities"
        )
        return 0.0, findings

    def _check_quality(self, details: dict) -> tuple[float, list[str]]:
        """Evaluate the Agent Card against A2A spec requirements."""
        findings = []
        data = details.get("a2a_data", {})
        score = 0.0

        # Required fields per A2A spec
        has_name = bool(data.get("name"))
        has_description = bool(data.get("description"))
        has_url = bool(data.get("url"))

        if has_name:
            score += 0.15
            details["a2a_name"] = data["name"]
        if has_description:
            score += 0.15
            details["a2a_description"] = str(data["description"])[:200]
        if has_url:
            score += 0.1

        # Skills/capabilities
        skills = data.get("skills", data.get("capabilities", []))
        if skills:
            score += 0.2
            details["a2a_skill_count"] = len(skills)
            findings.append(f"Agent Card declares {len(skills)} skill(s)")
        else:
            findings.append("Agent Card lacks skill/capability declarations")

        # Authentication info
        auth = data.get("authentication", data.get("auth", data.get("securitySchemes")))
        if auth:
            score += 0.15
            findings.append("Agent Card includes authentication requirements")
            details["a2a_has_auth"] = True
        else:
            details["a2a_has_auth"] = False

        # Provider info
        provider = data.get("provider", data.get("organization"))
        if provider:
            score += 0.1
            details["a2a_provider"] = str(provider)[:100]

        # Version
        version = data.get("version", data.get("protocolVersion"))
        if version:
            score += 0.05
            details["a2a_version"] = version

        # Supported protocols/input-output modes
        protocols = data.get("defaultInputModes", data.get("protocols", []))
        if protocols:
            score += 0.1
            details["a2a_protocols"] = protocols

        quality_summary = []
        if has_name:
            quality_summary.append("name")
        if has_description:
            quality_summary.append("description")
        if skills:
            quality_summary.append("skills")
        if auth:
            quality_summary.append("auth")
        findings.append(
            f"Agent Card includes: {', '.join(quality_summary) or 'minimal fields'}"
        )

        return min(score, 1.0), findings
