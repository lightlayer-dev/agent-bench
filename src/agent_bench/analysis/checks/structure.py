"""Check: HTML structure and navigability for agents."""

from __future__ import annotations

import httpx
from bs4 import BeautifulSoup

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


# Semantic HTML elements that indicate good structure
SEMANTIC_ELEMENTS = {"nav", "main", "article", "section", "aside", "header", "footer", "figure", "figcaption", "details", "summary"}

# Interactive elements that should have accessible labels
INTERACTIVE_ELEMENTS = {"button", "input", "select", "textarea", "a"}


class StructureCheck(BaseCheck):
    """Evaluate HTML structure and navigability.

    Checks for:
    - Semantic HTML elements (nav, main, article, section)
    - ARIA labels and roles
    - Form labels and input names
    - Predictable URL patterns
    - Stable CSS selectors / data-testid attributes
    - Client-side rendering vs server-side (SSR is more agent-friendly)
    """

    name = "structure"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        details: dict[str, object] = {}
        sub_scores: list[float] = []

        try:
            response = httpx.get(str(self.url), follow_redirects=True, timeout=15)
            html = response.text
        except httpx.HTTPError as e:
            return CheckResult(
                name=self.name, score=0.0,
                findings=[f"Failed to fetch page: {e}"],
            )

        soup = BeautifulSoup(html, "html.parser")

        # 1. Semantic HTML ratio
        semantic_score, semantic_findings = self._check_semantic_html(soup, details)
        sub_scores.append(semantic_score)
        findings.extend(semantic_findings)

        # 2. ARIA labels on interactive elements
        aria_score, aria_findings = self._check_aria_labels(soup, details)
        sub_scores.append(aria_score)
        findings.extend(aria_findings)

        # 3. Form accessibility
        form_score, form_findings = self._check_forms(soup, details)
        sub_scores.append(form_score)
        findings.extend(form_findings)

        # 4. Stable selectors (data-testid, data-cy, etc.)
        selector_score, selector_findings = self._check_stable_selectors(soup, details)
        sub_scores.append(selector_score)
        findings.extend(selector_findings)

        # 5. SSR detection (content without JS)
        ssr_score, ssr_findings = self._check_ssr(soup, details)
        sub_scores.append(ssr_score)
        findings.extend(ssr_findings)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0
        return CheckResult(name=self.name, score=overall, findings=findings, details=details)

    def _check_semantic_html(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check ratio of semantic elements to divs."""
        findings = []
        all_elements = soup.find_all(True)
        total = len(all_elements)
        if total == 0:
            return 0.0, ["No HTML elements found"]

        divs = len(soup.find_all("div"))
        semantic_count = sum(len(soup.find_all(tag)) for tag in SEMANTIC_ELEMENTS)

        details["total_elements"] = total
        details["div_count"] = divs
        details["semantic_count"] = semantic_count

        if semantic_count == 0:
            findings.append("No semantic HTML elements found (nav, main, article, etc.)")
            return 0.0, findings

        # Score based on semantic-to-div ratio
        ratio = semantic_count / max(divs, 1)
        score = min(ratio * 2, 1.0)  # ratio of 0.5 = full score

        if score >= 0.7:
            findings.append(f"Good semantic HTML: {semantic_count} semantic elements vs {divs} divs")
        elif score >= 0.3:
            findings.append(f"Moderate semantic HTML: {semantic_count} semantic elements vs {divs} divs")
        else:
            findings.append(f"Heavy div usage: {divs} divs with only {semantic_count} semantic elements")

        return score, findings

    def _check_aria_labels(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check if interactive elements have ARIA labels or accessible names."""
        findings = []
        interactive = soup.find_all(INTERACTIVE_ELEMENTS)
        total = len(interactive)

        if total == 0:
            return 1.0, ["No interactive elements to check"]

        labeled = 0
        for el in interactive:
            has_label = any([
                el.get("aria-label"),
                el.get("aria-labelledby"),
                el.get("title"),
                el.get("alt"),
                el.get("name"),
                el.get("id") and soup.find("label", attrs={"for": el.get("id")}),
                el.string and el.string.strip(),  # text content
            ])
            if has_label:
                labeled += 1

        score = labeled / total
        details["interactive_elements"] = total
        details["labeled_elements"] = labeled

        if score >= 0.8:
            findings.append(f"Good accessibility: {labeled}/{total} interactive elements have labels")
        else:
            findings.append(f"Poor accessibility: only {labeled}/{total} interactive elements have labels")

        return score, findings

    def _check_forms(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check form accessibility — labels, input types, names."""
        findings = []
        forms = soup.find_all("form")
        inputs = soup.find_all(["input", "select", "textarea"])

        if not inputs:
            return 1.0, ["No form inputs found"]

        named = sum(1 for inp in inputs if inp.get("name"))
        typed = sum(1 for inp in inputs if inp.get("type") and inp.name == "input")
        total_inputs = len([i for i in inputs if i.name == "input"])

        details["form_count"] = len(forms)
        details["input_count"] = len(inputs)
        details["named_inputs"] = named

        name_score = named / len(inputs) if inputs else 1.0
        type_score = typed / total_inputs if total_inputs else 1.0
        score = (name_score + type_score) / 2

        if score >= 0.8:
            findings.append(f"Forms are well-structured: {named}/{len(inputs)} inputs have names")
        else:
            findings.append(f"Forms need work: {named}/{len(inputs)} inputs have names, {typed}/{total_inputs} have types")

        return score, findings

    def _check_stable_selectors(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check for data-testid, data-cy, or similar stable selector attributes."""
        findings = []
        all_elements = soup.find_all(True)
        total = len(all_elements)

        if total == 0:
            return 0.0, ["No elements found"]

        stable_attrs = ["data-testid", "data-cy", "data-test", "data-automation", "data-qa"]
        with_stable = 0
        for el in all_elements:
            if any(el.get(attr) for attr in stable_attrs):
                with_stable += 1

        details["elements_with_stable_selectors"] = with_stable

        if with_stable == 0:
            findings.append("No stable test selectors found (data-testid, data-cy, etc.)")
            return 0.0, findings

        # Even a few stable selectors is good — they're typically on key interactive elements
        score = min(with_stable / 10, 1.0)  # 10+ stable selectors = full score
        findings.append(f"Found {with_stable} elements with stable test selectors")

        return score, findings

    def _check_ssr(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Detect if the page is server-side rendered (has content without JS)."""
        findings = []

        # Check for meaningful text content (not just script tags)
        text = soup.get_text(strip=True)
        scripts = soup.find_all("script")
        noscript = soup.find_all("noscript")

        # Remove script content from text length estimate
        script_text_len = sum(len(s.get_text()) for s in scripts)
        content_len = len(text) - script_text_len

        details["content_length"] = content_len
        details["script_count"] = len(scripts)
        details["has_noscript"] = len(noscript) > 0

        # SPA indicators
        spa_indicators = [
            soup.find("div", id="root"),
            soup.find("div", id="app"),
            soup.find("div", id="__next"),
            soup.find("div", id="__nuxt"),
        ]
        is_spa = any(spa_indicators) and content_len < 200

        if is_spa:
            findings.append("Likely a client-side SPA — minimal server-rendered content")
            details["rendering"] = "client-side"
            return 0.2, findings

        if content_len > 500:
            findings.append("Good server-side rendering — content available without JavaScript")
            details["rendering"] = "server-side"
            return 1.0, findings

        if content_len > 100:
            findings.append("Some server-rendered content, but limited")
            details["rendering"] = "partial"
            return 0.6, findings

        findings.append("Very little content without JavaScript")
        details["rendering"] = "minimal"
        return 0.3, findings
