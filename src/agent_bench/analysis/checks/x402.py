"""Check: x402 Payment Protocol — HTTP-native micropayments for agents.

The x402 protocol (https://x402.org, https://github.com/coinbase/x402) enables
HTTP-native micropayments: server responds 402 with payment requirements, client
pays with stablecoin, retries with payment proof.

This check evaluates whether a site signals x402 support — a key indicator of
agent-monetisation readiness.
"""

from __future__ import annotations

import json

import httpx

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class X402Check(BaseCheck):
    """Evaluate x402 micropayment protocol support.

    Checks for:
    - HTTP 402 responses with Payment-Required headers
    - /.well-known/x402 discovery endpoint
    - Payment requirement structure (scheme, network, asset, amount)
    - Facilitator endpoint references
    """

    name = "x402"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. Check /.well-known/x402 discovery
        score, f = self._check_discovery(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. Check for 402 responses on common API paths
        score, f = self._check_402_responses(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 3. Check agents.txt or other signals for payment declarations
        score, f = self._check_payment_signals(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
        return CheckResult(name=self.name, score=overall, findings=findings, details=details)

    def _fetch(self, url: str, **kwargs) -> httpx.Response | None:
        try:
            return httpx.get(url, follow_redirects=True, timeout=10, **kwargs)
        except httpx.HTTPError:
            return None

    def _check_discovery(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for /.well-known/x402 or x402 info in discovery endpoints."""
        findings = []
        paths = ["/.well-known/x402", "/.well-known/x402.json"]

        for path in paths:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict) and len(data) > 0:
                        details["x402_discovery"] = True
                        details["x402_discovery_path"] = path
                        details["x402_config"] = {
                            k: v for k, v in data.items()
                            if k in ("scheme", "network", "asset", "facilitator", "payTo", "version")
                        }
                        findings.append(f"x402 discovery endpoint found at {path}")
                        return 1.0, findings
                except (json.JSONDecodeError, ValueError):
                    pass

        # Also check /.well-known/ai for x402 references
        resp = self._fetch(f"{base_url}/.well-known/ai")
        if resp and resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict) and ("x402" in str(data).lower() or "payment" in str(data).lower()):
                    details["x402_in_ai_discovery"] = True
                    findings.append("Payment/x402 references found in /.well-known/ai")
                    return 0.5, findings
            except (json.JSONDecodeError, ValueError):
                pass

        details["x402_discovery"] = False
        findings.append("No x402 discovery endpoint found")
        return 0.0, findings

    def _check_402_responses(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check if any endpoints return HTTP 402 with payment requirements."""
        findings = []
        test_paths = ["/api", "/api/v1", "/api/premium", "/premium", "/paid"]

        for path in test_paths:
            try:
                resp = httpx.get(
                    f"{base_url}{path}",
                    follow_redirects=False,
                    timeout=10,
                )
                if resp.status_code == 402:
                    # Check for Payment-Required header
                    payment_header = resp.headers.get("payment-required", "")
                    details["x402_402_found"] = True
                    details["x402_402_path"] = path

                    if payment_header:
                        details["x402_has_payment_header"] = True
                        findings.append(
                            f"HTTP 402 with Payment-Required header at {path} — "
                            "x402 protocol active"
                        )
                        return 1.0, findings
                    else:
                        findings.append(
                            f"HTTP 402 at {path} but no Payment-Required header — "
                            "partial x402 support"
                        )
                        return 0.5, findings
            except httpx.HTTPError:
                continue

        details["x402_402_found"] = False
        findings.append("No HTTP 402 responses detected on common paths")
        return 0.0, findings

    def _check_payment_signals(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for payment signals in other discovery files."""
        findings = []

        # Check agents.txt for payment references
        for path in ["/agents.txt", "/.well-known/agents.txt"]:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200:
                text_lower = resp.text.lower()
                if "payment:" in text_lower or "x402" in text_lower or "monetiz" in text_lower:
                    details["x402_in_agents_txt"] = True
                    findings.append("Payment/x402 references found in agents.txt")
                    return 0.5, findings

        # Check for payment-related meta tags or headers
        resp = self._fetch(base_url)
        if resp and resp.status_code == 200:
            # Check for payment headers
            has_payment_header = any(
                "payment" in k.lower() or "x402" in k.lower()
                for k in resp.headers.keys()
            )
            if has_payment_header:
                details["x402_payment_headers"] = True
                findings.append("Payment-related headers detected")
                return 0.5, findings

        findings.append("No payment protocol signals detected")
        return 0.0, findings
