"""Check: Machine-readable documentation quality."""

from __future__ import annotations

import json

import httpx
from bs4 import BeautifulSoup

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class DocsCheck(BaseCheck):
    """Evaluate documentation quality for agent consumption.

    Checks for:
    - robots.txt availability and agent-friendliness
    - sitemap.xml presence
    - OpenAPI/Swagger specifications
    - Structured data (JSON-LD, microdata)
    - llms.txt (emerging standard for LLM-friendly docs)
    """

    name = "docs"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. robots.txt
        score, f = self._check_robots(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. sitemap.xml
        score, f = self._check_sitemap(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 3. OpenAPI / Swagger spec
        score, f = self._check_openapi(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 4. Structured data (JSON-LD)
        score, f = self._check_structured_data(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 5. llms.txt
        score, f = self._check_llms_txt(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
        return CheckResult(
            name=self.name, score=overall, findings=findings, details=details
        )

    def _fetch(self, url: str) -> httpx.Response | None:
        """Fetch a URL, returning None on failure."""
        try:
            return httpx.get(url, follow_redirects=True, timeout=10)
        except httpx.HTTPError:
            return None

    def _check_robots(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check robots.txt for existence and agent-friendliness."""
        findings = []
        resp = self._fetch(f"{base_url}/robots.txt")

        if resp is None or resp.status_code != 200:
            details["robots_txt"] = False
            findings.append("No robots.txt found")
            return 0.0, findings

        text = resp.text.lower()
        details["robots_txt"] = True

        # Check if bots are blocked
        if "disallow: /" in text and "user-agent: *" in text:
            # Check if it's a blanket block vs selective
            lines = text.split("\n")
            blanket_block = False
            for i, line in enumerate(lines):
                if "user-agent: *" in line:
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if (
                            "disallow: /" == lines[j].strip()
                            or "disallow: / " in lines[j]
                        ):
                            blanket_block = True
                            break

            if blanket_block:
                findings.append("robots.txt blocks all bots (Disallow: /)")
                details["robots_blocks_all"] = True
                return 0.2, findings

        # Check for sitemap reference
        has_sitemap_ref = "sitemap:" in text
        details["robots_has_sitemap_ref"] = has_sitemap_ref

        # Check for specific AI bot rules
        ai_bots = [
            "gptbot",
            "chatgpt",
            "anthropic",
            "claude",
            "google-extended",
            "ccbot",
        ]
        blocked_bots = [bot for bot in ai_bots if bot in text]
        details["blocked_ai_bots"] = blocked_bots

        if blocked_bots:
            findings.append(f"robots.txt blocks AI bots: {', '.join(blocked_bots)}")
            score = 0.4
        else:
            findings.append(
                "robots.txt is present and doesn't specifically block AI bots"
            )
            score = 0.8

        if has_sitemap_ref:
            score = min(score + 0.2, 1.0)
            findings.append("robots.txt references a sitemap")

        return score, findings

    def _check_sitemap(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for sitemap.xml."""
        findings = []
        resp = self._fetch(f"{base_url}/sitemap.xml")

        if resp is None or resp.status_code != 200:
            details["sitemap"] = False
            findings.append("No sitemap.xml found")
            return 0.0, findings

        details["sitemap"] = True
        content = resp.text

        # Count URLs in sitemap
        url_count = content.lower().count("<url>") or content.lower().count("<loc>")
        details["sitemap_urls"] = url_count

        if url_count > 0:
            findings.append(f"sitemap.xml found with ~{url_count} URLs")
            return 1.0, findings
        else:
            findings.append("sitemap.xml exists but appears empty or malformed")
            return 0.5, findings

    def _check_openapi(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for OpenAPI/Swagger specifications."""
        findings = []
        spec_paths = [
            "/openapi.json",
            "/openapi.yaml",
            "/swagger.json",
            "/swagger.yaml",
            "/api-docs",
            "/api/docs",
            "/docs/api",
            "/.well-known/openapi.json",
        ]

        for path in spec_paths:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200:
                content_type = resp.headers.get("content-type", "")
                if (
                    "json" in content_type
                    or "yaml" in content_type
                    or "text" in content_type
                ):
                    try:
                        data = resp.json() if "json" in content_type else {}
                        if "openapi" in data or "swagger" in data or "paths" in data:
                            details["openapi_path"] = path
                            details["openapi_version"] = data.get(
                                "openapi", data.get("swagger", "unknown")
                            )
                            path_count = len(data.get("paths", {}))
                            details["openapi_endpoints"] = path_count
                            findings.append(
                                f"OpenAPI spec found at {path} with {path_count} endpoints"
                            )
                            return 1.0, findings
                    except (json.JSONDecodeError, ValueError):
                        pass

        details["openapi"] = False
        findings.append("No OpenAPI/Swagger specification found")
        return 0.0, findings

    def _check_structured_data(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Check for JSON-LD structured data in the page."""
        findings = []
        resp = self._fetch(base_url)

        if resp is None or resp.status_code != 200:
            return 0.0, ["Could not fetch page for structured data check"]

        soup = BeautifulSoup(resp.text, "html.parser")
        ld_scripts = soup.find_all("script", type="application/ld+json")

        if not ld_scripts:
            details["json_ld"] = False
            findings.append("No JSON-LD structured data found")
            return 0.0, findings

        details["json_ld"] = True
        details["json_ld_count"] = len(ld_scripts)

        # Try to parse and identify types
        types = []
        for script in ld_scripts:
            try:
                data = json.loads(script.string or "")
                if isinstance(data, dict):
                    t = data.get("@type", "unknown")
                    types.append(t)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            types.append(item.get("@type", "unknown"))
            except (json.JSONDecodeError, TypeError):
                pass

        details["json_ld_types"] = types
        findings.append(
            f"Found {len(ld_scripts)} JSON-LD blocks: {', '.join(types[:5])}"
        )

        return 1.0, findings

    def _check_llms_txt(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for llms.txt (emerging standard for LLM-friendly documentation)."""
        findings = []

        for path in ["/llms.txt", "/.well-known/llms.txt", "/llms-full.txt"]:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200 and len(resp.text) > 20:
                details["llms_txt"] = True
                details["llms_txt_path"] = path
                details["llms_txt_length"] = len(resp.text)
                findings.append(f"llms.txt found at {path} ({len(resp.text)} chars)")
                return 1.0, findings

        details["llms_txt"] = False
        findings.append("No llms.txt found (emerging standard for LLM-friendly docs)")
        return 0.0, findings
