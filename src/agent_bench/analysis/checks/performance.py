"""Check: Performance characteristics relevant to AI agents.

Measures response time, payload size, redirect chains, resource count,
and compression — all factors that affect how quickly and reliably an
agent can interact with a site.
"""

from __future__ import annotations

import time

import httpx
from bs4 import BeautifulSoup

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


# Thresholds
FAST_RESPONSE_MS = 500
SLOW_RESPONSE_MS = 3000
SMALL_PAYLOAD_KB = 100
LARGE_PAYLOAD_KB = 1000
MAX_REDIRECTS = 2
MAX_SCRIPTS = 20
MAX_STYLESHEETS = 10


class PerformanceCheck(BaseCheck):
    """Evaluate site performance from an agent's perspective.

    Checks:
    - Response time (TTFB)
    - Response payload size
    - Redirect chain length
    - Resource count (scripts, stylesheets, images)
    - Compression (gzip/br)
    """

    name = "performance"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        try:
            start = time.monotonic()
            response = httpx.get(
                str(self.url),
                follow_redirects=True,
                timeout=15,
                headers={"Accept-Encoding": "gzip, deflate, br"},
            )
            elapsed_ms = (time.monotonic() - start) * 1000
        except httpx.HTTPError as e:
            return CheckResult(
                name=self.name, score=0.0,
                findings=[f"Failed to fetch page: {e}"],
            )

        html = response.text

        # 1. Response time
        score, msgs = self._check_response_time(elapsed_ms, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 2. Payload size
        score, msgs = self._check_payload_size(response, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 3. Redirect chain
        score, msgs = self._check_redirects(response, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 4. Resource count
        soup = BeautifulSoup(html, "html.parser")
        score, msgs = self._check_resources(soup, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 5. Compression
        score, msgs = self._check_compression(response, details)
        sub_scores.append(score)
        findings.extend(msgs)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0

        return CheckResult(
            name=self.name,
            score=round(overall, 3),
            findings=findings,
            details=details,
        )

    def _check_response_time(self, elapsed_ms: float, details: dict) -> tuple[float, list[str]]:
        """Score based on time-to-first-byte."""
        findings: list[str] = []
        details["response_time_ms"] = round(elapsed_ms, 1)

        if elapsed_ms <= FAST_RESPONSE_MS:
            findings.append(f"Fast response: {elapsed_ms:.0f}ms")
            return 1.0, findings
        elif elapsed_ms <= SLOW_RESPONSE_MS:
            # Linear interpolation between fast and slow
            score = 1.0 - (elapsed_ms - FAST_RESPONSE_MS) / (SLOW_RESPONSE_MS - FAST_RESPONSE_MS)
            findings.append(f"Moderate response time: {elapsed_ms:.0f}ms")
            return round(max(0.3, score), 3), findings
        else:
            findings.append(f"Slow response: {elapsed_ms:.0f}ms — agents will timeout or retry")
            return 0.1, findings

    def _check_payload_size(self, response: httpx.Response, details: dict) -> tuple[float, list[str]]:
        """Score based on HTML payload size."""
        findings: list[str] = []

        size_bytes = len(response.content)
        size_kb = size_bytes / 1024
        details["payload_size_kb"] = round(size_kb, 1)

        if size_kb <= SMALL_PAYLOAD_KB:
            findings.append(f"Compact payload: {size_kb:.0f}KB")
            return 1.0, findings
        elif size_kb <= LARGE_PAYLOAD_KB:
            score = 1.0 - (size_kb - SMALL_PAYLOAD_KB) / (LARGE_PAYLOAD_KB - SMALL_PAYLOAD_KB)
            findings.append(f"Moderate payload: {size_kb:.0f}KB")
            return round(max(0.3, score), 3), findings
        else:
            findings.append(f"Large payload: {size_kb:.0f}KB — increases token cost for agents")
            return 0.1, findings

    def _check_redirects(self, response: httpx.Response, details: dict) -> tuple[float, list[str]]:
        """Score based on redirect chain length."""
        findings: list[str] = []

        redirect_count = len(response.history)
        details["redirect_count"] = redirect_count
        details["redirect_chain"] = [str(r.url) for r in response.history]

        if redirect_count == 0:
            findings.append("No redirects — direct access")
            return 1.0, findings
        elif redirect_count <= MAX_REDIRECTS:
            findings.append(f"{redirect_count} redirect(s) — acceptable")
            return 0.8, findings
        else:
            findings.append(f"{redirect_count} redirects — long chain slows agents and may cause loops")
            return max(0.1, 1.0 - redirect_count * 0.2), findings

    def _check_resources(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Score based on number of linked resources (scripts, styles, images)."""
        findings: list[str] = []

        scripts = soup.find_all("script", src=True)
        stylesheets = soup.find_all("link", rel="stylesheet")
        images = soup.find_all("img")
        iframes = soup.find_all("iframe")

        details["script_count"] = len(scripts)
        details["stylesheet_count"] = len(stylesheets)
        details["image_count"] = len(images)
        details["iframe_count"] = len(iframes)

        score = 1.0
        parts: list[str] = []

        if len(scripts) > MAX_SCRIPTS:
            score -= 0.3
            parts.append(f"{len(scripts)} scripts (heavy JS)")
        elif len(scripts) > MAX_SCRIPTS // 2:
            score -= 0.1
            parts.append(f"{len(scripts)} scripts")

        if len(stylesheets) > MAX_STYLESHEETS:
            score -= 0.2
            parts.append(f"{len(stylesheets)} stylesheets")
        elif len(stylesheets) > MAX_STYLESHEETS // 2:
            score -= 0.1
            parts.append(f"{len(stylesheets)} stylesheets")

        if len(iframes) > 3:
            score -= 0.2
            parts.append(f"{len(iframes)} iframes")

        if parts:
            findings.append(f"Resource heavy: {', '.join(parts)}")
        else:
            findings.append(f"Lean resources: {len(scripts)} scripts, {len(stylesheets)} styles, {len(images)} images")

        return round(max(0.1, score), 3), findings

    def _check_compression(self, response: httpx.Response, details: dict) -> tuple[float, list[str]]:
        """Check if the response uses compression."""
        findings: list[str] = []

        encoding = response.headers.get("content-encoding", "").lower()
        details["content_encoding"] = encoding or "none"

        if encoding in ("gzip", "br", "deflate", "zstd"):
            findings.append(f"Compression enabled: {encoding}")
            return 1.0, findings
        else:
            findings.append("No compression — larger transfers for agents")
            return 0.3, findings
