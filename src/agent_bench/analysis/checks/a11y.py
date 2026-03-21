"""Check: Accessibility features that improve agent navigability."""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


# ARIA landmark roles
LANDMARK_ROLES = {"banner", "navigation", "main", "complementary", "contentinfo", "search", "form", "region"}

# HTML5 elements that implicitly map to landmark roles
IMPLICIT_LANDMARKS = {
    "header": "banner",
    "nav": "navigation",
    "main": "main",
    "aside": "complementary",
    "footer": "contentinfo",
}


class A11yCheck(BaseCheck):
    """Evaluate accessibility features relevant to AI agents.

    Good accessibility helps agents because:
    - Landmarks provide structural navigation anchors
    - Alt text gives image understanding without vision
    - Skip links reveal page structure
    - ARIA live regions signal dynamic content
    - Proper tab order indicates interactive element flow
    """

    name = "a11y"

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

        # 1. Landmark coverage
        score, msgs = self._check_landmarks(soup, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 2. Image alt text
        score, msgs = self._check_alt_text(soup, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 3. Skip links
        score, msgs = self._check_skip_links(soup, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 4. ARIA live regions (dynamic content signals)
        score, msgs = self._check_live_regions(soup, details)
        sub_scores.append(score)
        findings.extend(msgs)

        # 5. Focus indicators (tabindex usage)
        score, msgs = self._check_focus_management(soup, details)
        sub_scores.append(score)
        findings.extend(msgs)

        overall = sum(sub_scores) / len(sub_scores) if sub_scores else 0.0

        return CheckResult(
            name=self.name,
            score=round(overall, 3),
            findings=findings,
            details=details,
        )

    def _check_landmarks(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check for ARIA landmark roles and implicit landmark elements."""
        findings: list[str] = []

        # Explicit role attributes
        explicit = soup.find_all(attrs={"role": True})
        landmark_roles_found = set()
        for el in explicit:
            role = el.get("role", "")
            if isinstance(role, str) and role.lower() in LANDMARK_ROLES:
                landmark_roles_found.add(role.lower())

        # Implicit landmark elements
        implicit_found = set()
        for tag_name, role in IMPLICIT_LANDMARKS.items():
            if soup.find(tag_name):
                implicit_found.add(role)

        all_landmarks = landmark_roles_found | implicit_found
        details["landmarks_found"] = sorted(all_landmarks)
        details["landmark_count"] = len(all_landmarks)

        # Need at least main + navigation for a good score
        essential = {"main", "navigation"}
        has_essential = essential.issubset(all_landmarks)

        if not all_landmarks:
            findings.append("No landmark roles or elements found — agents cannot navigate page structure")
            return 0.0, findings

        if has_essential:
            # Bonus for having more landmarks
            score = min(1.0, 0.7 + 0.1 * (len(all_landmarks) - 2))
            findings.append(f"Good landmark coverage: {', '.join(sorted(all_landmarks))}")
        else:
            missing = essential - all_landmarks
            findings.append(f"Missing essential landmarks: {', '.join(sorted(missing))}")
            score = 0.3 * (len(all_landmarks) / len(essential))

        return round(score, 3), findings

    def _check_alt_text(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check that images have alt text."""
        findings: list[str] = []

        images = soup.find_all("img")
        if not images:
            details["images_total"] = 0
            details["images_with_alt"] = 0
            findings.append("No images found")
            return 1.0, findings  # No images = no problem

        with_alt = 0
        empty_alt = 0  # Decorative images (alt="") are valid
        missing_alt = 0

        for img in images:
            alt = img.get("alt")
            if alt is None:
                missing_alt += 1
            elif alt.strip() == "":
                empty_alt += 1
            else:
                with_alt += 1

        total = len(images)
        details["images_total"] = total
        details["images_with_alt"] = with_alt
        details["images_decorative"] = empty_alt
        details["images_missing_alt"] = missing_alt

        # Missing alt is bad; empty alt (decorative) is fine
        valid = with_alt + empty_alt
        ratio = valid / total if total > 0 else 0

        if missing_alt == 0:
            findings.append(f"All {total} images have alt attributes ({with_alt} descriptive, {empty_alt} decorative)")
        else:
            findings.append(f"{missing_alt}/{total} images missing alt text — agents can't understand these images")

        return round(ratio, 3), findings

    def _check_skip_links(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check for skip navigation links (first links pointing to #id anchors)."""
        findings: list[str] = []

        # Look for links with href starting with # in the first few elements
        all_links = soup.find_all("a", href=True)
        skip_links = []

        for link in all_links[:20]:  # Check first 20 links
            href = link.get("href", "")
            if isinstance(href, str) and href.startswith("#") and len(href) > 1:
                text = link.get_text(strip=True).lower()
                # Common skip link patterns
                if any(kw in text for kw in ["skip", "jump", "main", "content", "navigation"]):
                    skip_links.append({"href": href, "text": link.get_text(strip=True)})

        details["skip_links"] = skip_links

        if skip_links:
            findings.append(f"Found {len(skip_links)} skip link(s) — helps agents jump to main content")
            return 1.0, findings
        else:
            findings.append("No skip links found — agents must traverse entire page to find content")
            return 0.0, findings

    def _check_live_regions(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check for ARIA live regions that signal dynamic content updates."""
        findings: list[str] = []

        live_regions = soup.find_all(attrs={"aria-live": True})
        status_roles = soup.find_all(attrs={"role": re.compile(r"^(status|alert|log|timer|marquee)$")})

        total = len(live_regions) + len(status_roles)
        details["live_regions"] = total
        details["aria_live_values"] = [el.get("aria-live") for el in live_regions]

        if total > 0:
            findings.append(f"Found {total} live region(s) — agents can detect dynamic content changes")
            return 1.0, findings
        else:
            # Not having live regions is OK for static sites, so partial score
            findings.append("No ARIA live regions — dynamic content changes may be invisible to agents")
            return 0.5, findings

    def _check_focus_management(self, soup: BeautifulSoup, details: dict) -> tuple[float, list[str]]:
        """Check focus management: tabindex usage, focus traps."""
        findings: list[str] = []

        tabindex_els = soup.find_all(attrs={"tabindex": True})
        positive_tabindex = []
        negative_tabindex = []
        zero_tabindex = []

        for el in tabindex_els:
            try:
                val = int(el.get("tabindex", 0))
            except (ValueError, TypeError):
                continue
            if val > 0:
                positive_tabindex.append(val)
            elif val < 0:
                negative_tabindex.append(val)
            else:
                zero_tabindex.append(val)

        details["tabindex_positive"] = len(positive_tabindex)
        details["tabindex_zero"] = len(zero_tabindex)
        details["tabindex_negative"] = len(negative_tabindex)

        score = 0.5  # Baseline

        if positive_tabindex:
            # Positive tabindex is generally bad practice (overrides natural order)
            findings.append(f"Found {len(positive_tabindex)} elements with positive tabindex — may confuse agent tab navigation")
            score -= 0.2

        if zero_tabindex:
            # tabindex=0 makes custom elements focusable — good
            findings.append(f"{len(zero_tabindex)} custom elements made focusable via tabindex=0")
            score += 0.3

        if negative_tabindex:
            # tabindex=-1 is fine (programmatic focus)
            findings.append(f"{len(negative_tabindex)} elements with tabindex=-1 (programmatic focus)")
            score += 0.1

        if not tabindex_els:
            findings.append("No custom tabindex — relying on natural focus order (fine for simple pages)")
            score = 0.7

        return round(max(0.0, min(1.0, score)), 3), findings
