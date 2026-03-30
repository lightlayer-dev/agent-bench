"""Check: API surface availability and quality."""

from __future__ import annotations

import json

import httpx

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult

# Common API path patterns to probe
API_PATHS = [
    "/api",
    "/api/v1",
    "/api/v2",
    "/v1",
    "/v2",
    "/rest",
    "/rest/v1",
    "/graphql",
    "/gql",
]

# Paths that commonly expose API documentation or specs
SPEC_PATHS = [
    "/openapi.json",
    "/openapi.yaml",
    "/swagger.json",
    "/swagger.yaml",
    "/swagger/v1/swagger.json",
    "/api-docs",
    "/api/docs",
    "/docs/api",
    "/.well-known/openapi.json",
    "/redoc",
    "/api/schema",
]


class APICheck(BaseCheck):
    """Evaluate API availability and quality.

    Checks for:
    - REST API endpoints (common paths like /api, /api/v1, etc.)
    - GraphQL endpoint availability
    - Response format quality (JSON vs HTML)
    - CORS headers (Access-Control-Allow-Origin)
    - Content negotiation (Accept header handling)
    - Pagination indicators
    """

    name = "api"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. Probe for API endpoints
        score, f = self._check_api_endpoints(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. Check for GraphQL
        score, f = self._check_graphql(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 3. CORS headers
        score, f = self._check_cors(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 4. Content negotiation
        score, f = self._check_content_negotiation(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
        return CheckResult(
            name=self.name, score=overall, findings=findings, details=details
        )

    def _fetch(self, url: str, **kwargs) -> httpx.Response | None:
        """Fetch a URL, returning None on failure."""
        try:
            return httpx.get(url, follow_redirects=True, timeout=10, **kwargs)
        except httpx.HTTPError:
            return None

    def _check_api_endpoints(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Probe common API paths and evaluate response quality."""
        findings = []
        discovered: list[dict[str, object]] = []

        # Fetch the main page to detect SPA catch-all behavior
        main_resp = self._fetch(base_url)
        main_body_hash = None
        if main_resp and main_resp.status_code == 200:
            # Hash first 500 chars to detect SPA catch-all (same HTML for every route)
            main_body_hash = hash(main_resp.text[:500])

        for path in API_PATHS:
            url = f"{base_url}{path}"
            resp = self._fetch(url, headers={"Accept": "application/json"})

            if resp is None or resp.status_code in (404, 403, 401, 405, 500):
                continue

            content_type = resp.headers.get("content-type", "")
            is_json = "json" in content_type

            # SPA false positive detection: if the response is HTML and matches
            # the main page, this is a catch-all route, not a real API endpoint
            if not is_json and "html" in content_type:
                if main_body_hash and hash(resp.text[:500]) == main_body_hash:
                    continue  # Skip — this is the SPA serving the same shell
                # Even if it's different HTML, an HTML response to an
                # Accept: application/json request is not a real API
                continue

            endpoint_info: dict[str, object] = {
                "path": path,
                "status": resp.status_code,
                "content_type": content_type,
                "is_json": is_json,
            }

            # Check for pagination indicators
            if is_json:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        pagination_keys = {
                            "next",
                            "previous",
                            "page",
                            "total",
                            "count",
                            "per_page",
                            "page_size",
                            "cursor",
                            "offset",
                            "limit",
                        }
                        found_pagination = pagination_keys & set(data.keys())
                        if found_pagination:
                            endpoint_info["pagination"] = list(found_pagination)

                        # Check for hypermedia links
                        if "_links" in data or "links" in data:
                            endpoint_info["hypermedia"] = True
                except (json.JSONDecodeError, ValueError):
                    pass

            # Check Link header for pagination
            link_header = resp.headers.get("link", "")
            if link_header and ("next" in link_header or "prev" in link_header):
                endpoint_info["link_header_pagination"] = True

            discovered.append(endpoint_info)

        details["discovered_endpoints"] = discovered
        details["endpoint_count"] = len(discovered)

        if not discovered:
            findings.append("No API endpoints found at common paths")
            return 0.0, findings

        # Score based on quantity and quality
        json_endpoints = sum(1 for e in discovered if e.get("is_json"))
        paginated = sum(
            1
            for e in discovered
            if e.get("pagination") or e.get("link_header_pagination")
        )

        findings.append(
            f"Found {len(discovered)} API endpoints ({json_endpoints} returning JSON)"
        )
        if paginated:
            findings.append(f"{paginated} endpoints show pagination support")

        score = min(len(discovered) / 3, 1.0)  # 3+ endpoints = full base score
        if json_endpoints > 0:
            score = max(score, 0.5)  # At least 0.5 if any JSON
        if paginated:
            score = min(score + 0.2, 1.0)

        return score, findings

    def _check_graphql(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for a GraphQL endpoint."""
        findings = []
        graphql_paths = ["/graphql", "/gql", "/api/graphql"]

        for path in graphql_paths:
            url = f"{base_url}{path}"

            # GraphQL introspection query
            try:
                resp = httpx.post(
                    url,
                    json={"query": "{ __schema { types { name } } }"},
                    headers={"Content-Type": "application/json"},
                    timeout=10,
                )

                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if "data" in data and "__schema" in data.get("data", {}):
                            type_count = len(data["data"]["__schema"].get("types", []))
                            details["graphql"] = True
                            details["graphql_path"] = path
                            details["graphql_types"] = type_count
                            findings.append(
                                f"GraphQL endpoint at {path} with {type_count} types (introspection enabled)"
                            )
                            return 1.0, findings
                    except (json.JSONDecodeError, ValueError):
                        pass

                # Even a 400 with JSON error might indicate GraphQL exists
                if resp.status_code in (200, 400):
                    content_type = resp.headers.get("content-type", "")
                    if "json" in content_type:
                        details["graphql"] = True
                        details["graphql_path"] = path
                        details["graphql_introspection"] = False
                        findings.append(
                            f"GraphQL endpoint at {path} (introspection disabled)"
                        )
                        return 0.7, findings

            except httpx.HTTPError:
                continue

        details["graphql"] = False
        findings.append("No GraphQL endpoint found")
        return 0.0, findings

    def _check_cors(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Check for CORS headers."""
        findings = []

        # Send a preflight-like request
        resp = self._fetch(base_url)
        if resp is None:
            return 0.0, ["Could not check CORS headers"]

        cors_header = resp.headers.get("access-control-allow-origin", "")
        cors_methods = resp.headers.get("access-control-allow-methods", "")
        resp.headers.get("access-control-allow-headers", "")

        details["cors_origin"] = cors_header
        details["cors_methods"] = cors_methods

        if cors_header == "*":
            findings.append("CORS: open access (Access-Control-Allow-Origin: *)")
            return 1.0, findings
        elif cors_header:
            findings.append(f"CORS: restricted to {cors_header}")
            return 0.7, findings
        else:
            findings.append(
                "No CORS headers — API may not be accessible from browser-based agents"
            )
            return 0.2, findings

    def _check_content_negotiation(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Check if the server handles Accept headers properly."""
        findings = []

        # Request JSON
        resp_json = self._fetch(base_url, headers={"Accept": "application/json"})
        resp_html = self._fetch(base_url, headers={"Accept": "text/html"})

        if resp_json is None or resp_html is None:
            return 0.0, ["Could not test content negotiation"]

        json_ct = resp_json.headers.get("content-type", "")
        html_ct = resp_html.headers.get("content-type", "")

        details["content_negotiation"] = {
            "json_request_ct": json_ct,
            "html_request_ct": html_ct,
        }

        # If requesting JSON returns JSON, good content negotiation
        if "json" in json_ct and "html" in html_ct:
            findings.append(
                "Server supports content negotiation (responds to Accept headers)"
            )
            return 1.0, findings
        elif "json" in json_ct:
            findings.append("Server returns JSON by default")
            return 0.8, findings
        elif "html" in json_ct and "html" in html_ct:
            findings.append(
                "Server always returns HTML regardless of Accept header — no API content negotiation"
            )
            return 0.0, findings
        else:
            findings.append(
                "Server ignores Accept header — always returns same content type"
            )
            return 0.1, findings
