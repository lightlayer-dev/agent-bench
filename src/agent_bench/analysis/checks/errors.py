"""Check: Error handling and rate limiting quality."""

from __future__ import annotations

import json

import httpx

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class ErrorsCheck(BaseCheck):
    """Evaluate error handling quality for agents.

    Checks for:
    - 404 response quality (JSON vs HTML, structured vs generic)
    - Rate limit headers on normal responses
    - Error response format consistency
    - Meaningful HTTP status codes
    """

    name = "errors"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. 404 response quality
        score, f = self._check_404_quality(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. Rate limit headers
        score, f = self._check_rate_limit_headers(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 3. Method not allowed handling
        score, f = self._check_method_handling(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
        return CheckResult(
            name=self.name, score=overall, findings=findings, details=details
        )

    def _fetch(self, url: str, **kwargs) -> httpx.Response | None:
        try:
            return httpx.get(url, follow_redirects=True, timeout=10, **kwargs)
        except httpx.HTTPError:
            return None

    def _check_404_quality(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Hit a nonexistent path and evaluate the error response."""
        findings = []
        # Use a clearly nonexistent path
        resp = self._fetch(
            f"{base_url}/this-path-definitely-does-not-exist-agent-bench-test",
            headers={"Accept": "application/json"},
        )

        if resp is None:
            return 0.0, ["Could not fetch 404 test page"]

        details["404_status"] = resp.status_code
        content_type = resp.headers.get("content-type", "")
        details["404_content_type"] = content_type

        # Check if it returns proper 404
        if resp.status_code != 404:
            findings.append(
                f"Non-existent path returned {resp.status_code} instead of 404"
            )
            # Soft 404 (200 with "not found" page) is bad for agents
            if resp.status_code == 200:
                details["soft_404"] = True
                findings.append("Soft 404 detected — returns 200 for missing pages")
                return 0.1, findings
            return 0.3, findings

        # Check response format
        is_json = "json" in content_type
        details["404_is_json"] = is_json

        if is_json:
            try:
                data = resp.json()
                has_error_code = any(
                    k in data for k in ("error", "code", "error_code", "status")
                )
                has_message = any(
                    k in data for k in ("message", "detail", "description", "error")
                )
                details["404_structured"] = has_error_code or has_message

                if has_error_code and has_message:
                    findings.append(
                        "404 returns structured JSON error with code and message"
                    )
                    return 1.0, findings
                elif has_message:
                    findings.append("404 returns JSON with error message")
                    return 0.8, findings
                else:
                    findings.append(
                        "404 returns JSON but lacks structured error fields"
                    )
                    return 0.6, findings
            except (json.JSONDecodeError, ValueError):
                findings.append(
                    "404 claims JSON content-type but body is not valid JSON"
                )
                return 0.3, findings
        else:
            findings.append("404 returns HTML error page (not machine-readable)")
            return 0.3, findings

    def _check_rate_limit_headers(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Check for rate limiting headers on normal responses."""
        findings = []
        resp = self._fetch(base_url)

        if resp is None:
            return 0.0, ["Could not fetch page to check rate limit headers"]

        headers = {k.lower(): v for k, v in resp.headers.items()}
        rate_limit_headers: dict[str, str] = {}

        # Standard rate limit header patterns
        rl_patterns = [
            "x-ratelimit-limit",
            "x-ratelimit-remaining",
            "x-ratelimit-reset",
            "x-rate-limit-limit",
            "x-rate-limit-remaining",
            "x-rate-limit-reset",
            "ratelimit-limit",
            "ratelimit-remaining",
            "ratelimit-reset",
            "retry-after",
        ]

        for pattern in rl_patterns:
            if pattern in headers:
                rate_limit_headers[pattern] = headers[pattern]

        details["rate_limit_headers"] = rate_limit_headers

        if not rate_limit_headers:
            findings.append("No rate limit headers found")
            return 0.0, findings

        if "retry-after" in rate_limit_headers:
            findings.append(
                "Retry-After header present — agents can back off appropriately"
            )

        remaining_key = next((k for k in rate_limit_headers if "remaining" in k), None)
        limit_key = next(
            (
                k
                for k in rate_limit_headers
                if k.endswith("limit") and "remaining" not in k
            ),
            None,
        )

        if remaining_key and limit_key:
            findings.append(
                f"Full rate limit info: {limit_key}={rate_limit_headers[limit_key]}, {remaining_key}={rate_limit_headers[remaining_key]}"
            )
            return 1.0, findings

        findings.append(
            f"Partial rate limit headers: {', '.join(rate_limit_headers.keys())}"
        )
        return 0.6, findings

    def _check_method_handling(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Check how the server handles wrong HTTP methods."""
        findings = []

        try:
            # Send a DELETE to the main page — should get 405 Method Not Allowed
            resp = httpx.delete(base_url, follow_redirects=True, timeout=10)
        except httpx.HTTPError:
            return 0.0, ["Could not test HTTP method handling"]

        details["delete_main_status"] = resp.status_code
        resp.headers.get("content-type", "")

        if resp.status_code == 405:
            # Check for Allow header
            allow = resp.headers.get("allow", "")
            details["allow_header"] = allow

            if allow:
                findings.append(f"Proper 405 with Allow header: {allow}")
                return 1.0, findings
            else:
                findings.append("Returns 405 but missing Allow header")
                return 0.7, findings

        elif resp.status_code == 200:
            # Accepting DELETE on the main page is weird but not agent-hostile
            findings.append("Server accepts DELETE on main page (no method validation)")
            return 0.3, findings
        else:
            findings.append(
                f"Unexpected status {resp.status_code} for DELETE on main page"
            )
            return 0.4, findings
