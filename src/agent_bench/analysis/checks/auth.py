"""Check: Authentication complexity for agents."""

from __future__ import annotations


import httpx
from bs4 import BeautifulSoup

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


class AuthCheck(BaseCheck):
    """Evaluate authentication complexity.

    Checks for:
    - API key authentication options (simplest for agents)
    - OAuth / OpenID Connect discovery
    - CAPTCHA presence on key pages
    - Bot detection mechanisms (Cloudflare, Akamai, etc.)
    - Login form complexity

    Lower complexity = higher score (easier for agents).
    """

    name = "auth"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        base_url = str(self.url).rstrip("/")

        # 1. Bot detection / WAF
        score, f = self._check_bot_detection(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 2. CAPTCHA detection
        score, f = self._check_captcha(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 3. OAuth / OIDC discovery
        score, f = self._check_oauth_discovery(base_url, details)
        sub_scores.append(score)
        findings.extend(f)

        # 4. Login form analysis
        score, f = self._check_login_form(base_url, details)
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

    def _check_bot_detection(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Detect WAF / bot detection systems."""
        findings = []
        resp = self._fetch(base_url)

        if resp is None:
            return 0.0, ["Could not fetch site to check bot detection"]

        headers = {k.lower(): v for k, v in resp.headers.items()}
        html = resp.text.lower()
        detected: list[str] = []

        # Cloudflare
        if "cf-ray" in headers or "cf-cache-status" in headers:
            detected.append("Cloudflare")
            # Check for Cloudflare challenge page
            if "challenge-platform" in html or "cf-challenge" in html:
                detected.append("Cloudflare Challenge (active blocking)")

        # Akamai
        if "x-akamai" in " ".join(headers.keys()) or "akamai" in headers.get(
            "server", ""
        ):
            detected.append("Akamai")

        # AWS WAF
        if "x-amzn-waf" in " ".join(headers.keys()):
            detected.append("AWS WAF")

        # Imperva / Incapsula
        if "x-iinfo" in headers or "incap_ses" in resp.headers.get("set-cookie", ""):
            detected.append("Imperva/Incapsula")

        # DataDome
        if "datadome" in html or "datadome" in " ".join(headers.keys()):
            detected.append("DataDome")

        details["bot_detection"] = detected

        if not detected:
            findings.append("No bot detection systems detected")
            return 1.0, findings

        # Cloudflare alone is common and usually not aggressive
        if detected == ["Cloudflare"]:
            findings.append("Cloudflare detected (passive — no active challenge)")
            return 0.8, findings

        if any("challenge" in d.lower() or "blocking" in d.lower() for d in detected):
            findings.append(f"Active bot blocking detected: {', '.join(detected)}")
            return 0.1, findings

        findings.append(f"Bot detection systems: {', '.join(detected)}")
        return 0.5, findings

    def _check_captcha(self, base_url: str, details: dict) -> tuple[float, list[str]]:
        """Detect CAPTCHA presence on the main page and login."""
        findings = []
        captcha_indicators = [
            "recaptcha",
            "hcaptcha",
            "captcha",
            "g-recaptcha",
            "h-captcha",
            "cf-turnstile",
            "arkose",
        ]

        pages_to_check = [base_url]
        # Common login paths
        for path in ["/login", "/signin", "/sign-in", "/auth/login"]:
            pages_to_check.append(f"{base_url}{path}")

        captcha_found: list[str] = []

        for url in pages_to_check:
            resp = self._fetch(url)
            if resp is None or resp.status_code in (404, 403):
                continue

            html = resp.text.lower()
            for indicator in captcha_indicators:
                if indicator in html and indicator not in captcha_found:
                    captcha_found.append(indicator)

        details["captcha_detected"] = captcha_found

        if not captcha_found:
            findings.append("No CAPTCHA detected on main page or login")
            return 1.0, findings

        findings.append(f"CAPTCHA detected: {', '.join(captcha_found)}")
        # CAPTCHAs are a significant barrier for agents
        return 0.2, findings

    def _check_oauth_discovery(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Check for OAuth/OIDC well-known endpoints."""
        findings = []
        discovery_paths = [
            "/.well-known/openid-configuration",
            "/.well-known/oauth-authorization-server",
        ]

        for path in discovery_paths:
            resp = self._fetch(f"{base_url}{path}")
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    grant_types = data.get("grant_types_supported", [])
                    details["oauth_discovery"] = True
                    details["oauth_path"] = path
                    details["oauth_grant_types"] = grant_types

                    # client_credentials is the best for agents (machine-to-machine)
                    if "client_credentials" in grant_types:
                        findings.append(
                            "OAuth discovery found — supports client_credentials (machine-to-machine)"
                        )
                        return 1.0, findings
                    else:
                        findings.append(
                            f"OAuth discovery found — grant types: {', '.join(grant_types)}"
                        )
                        return 0.7, findings
                except (ValueError, KeyError):
                    pass

        details["oauth_discovery"] = False
        # No OAuth discovery isn't necessarily bad — could use API keys
        findings.append("No OAuth/OIDC discovery endpoint found")
        return 0.5, findings

    def _check_login_form(
        self, base_url: str, details: dict
    ) -> tuple[float, list[str]]:
        """Analyze login form complexity."""
        findings = []
        login_paths = ["/login", "/signin", "/sign-in", "/auth/login", "/account/login"]

        for path in login_paths:
            resp = self._fetch(f"{base_url}{path}")
            if resp is None or resp.status_code in (404, 403, 405):
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            forms = soup.find_all("form")

            if not forms:
                continue

            # Analyze the first form
            form = forms[0]
            inputs = form.find_all("input")
            input_types = [inp.get("type", "text") for inp in inputs]

            details["login_form_found"] = True
            details["login_path"] = path
            details["login_input_types"] = input_types

            # Check complexity indicators
            has_csrf = any(
                str(inp.get("name", "")).lower()
                in (
                    "csrf",
                    "_token",
                    "csrf_token",
                    "csrfmiddlewaretoken",
                    "authenticity_token",
                )
                for inp in inputs
            )
            has_hidden = input_types.count("hidden")
            password_fields = input_types.count("password")

            details["login_has_csrf"] = has_csrf
            details["login_hidden_inputs"] = has_hidden

            if password_fields == 0:
                # Might be SSO-only
                findings.append(
                    f"Login form at {path} — no password field (possibly SSO/OAuth only)"
                )
                return 0.7, findings

            complexity = "simple"
            score = 0.6

            if has_hidden > 3:
                complexity = "complex"
                score = 0.3
            elif has_csrf:
                complexity = "moderate (CSRF protected)"
                score = 0.5

            findings.append(
                f"Login form at {path} — {complexity}, {len(inputs)} inputs"
            )
            return score, findings

        details["login_form_found"] = False
        findings.append("No login form found at common paths")
        return 0.8, findings  # No login needed = agent-friendly
