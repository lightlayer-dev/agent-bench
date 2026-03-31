"""Check: Token cost efficiency for AI agents.

Measures how expensive a website is for an agent to interact with by
analyzing DOM bloat, payload sizes, and signal-to-noise ratio.
"""

from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup, Comment

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult


# Average characters per token (rough estimate across models)
CHARS_PER_TOKEN = 4

# Thresholds
MAX_EFFICIENT_PAGE_TOKENS = 4_000  # A well-optimized page
MAX_ACCEPTABLE_PAGE_TOKENS = 15_000  # Starts getting expensive
GOOD_SIGNAL_RATIO = 0.4  # 40%+ of content is meaningful
POOR_SIGNAL_RATIO = 0.15  # Below 15% is mostly noise

# Pricing per million input tokens (USD, as of early 2026)
MODEL_PRICING = {
    "claude-sonnet": 3.00,
    "gpt-4o": 2.50,
    "claude-opus": 15.00,
    "gemini-pro": 1.25,
}

# Elements that are pure noise for agents
NOISE_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "iframe",
    "canvas",
    "template",
    "link",
    "meta",
}

# Attributes that add tokens but no value for agents
NOISE_ATTRS = {
    "data-reactid",
    "data-reactroot",
    "data-styled",
    "data-emotion",
    "data-testid",
    "data-cy",
    "class",  # Often very long utility class strings
}


class CostCheck(BaseCheck):
    """Evaluate token cost efficiency for AI agents.

    Checks for:
    - Page token count (raw HTML → estimated tokens)
    - Signal-to-noise ratio (meaningful content vs boilerplate)
    - DOM bloat (unnecessary nesting depth, empty elements)
    - Response payload size (JSON API responses)
    - Inline script/style bloat
    """

    name = "cost"

    def execute(self) -> CheckResult:
        findings: list[str] = []
        deductions = 0.0

        try:
            resp = httpx.get(self.url, follow_redirects=True, timeout=15)
        except httpx.HTTPError as e:
            return CheckResult(
                name=self.name,
                score=0.0,
                findings=[f"Failed to fetch: {e}"],
            )

        raw_html = resp.text
        raw_tokens = len(raw_html) / CHARS_PER_TOKEN

        # 1. Raw page token count
        if raw_tokens > MAX_ACCEPTABLE_PAGE_TOKENS:
            deductions += 0.30
            findings.append(
                f"Page is ~{raw_tokens:,.0f} tokens raw — very expensive for agents "
                f"(>{MAX_ACCEPTABLE_PAGE_TOKENS:,} threshold)"
            )
        elif raw_tokens > MAX_EFFICIENT_PAGE_TOKENS:
            deductions += 0.15
            findings.append(f"Page is ~{raw_tokens:,.0f} tokens raw — moderate cost")
        else:
            findings.append(f"Page is ~{raw_tokens:,.0f} tokens raw — efficient")

        soup = BeautifulSoup(raw_html, "html.parser")

        # 2. Signal-to-noise ratio
        signal_text, noise_size = self._compute_signal_noise(soup, raw_html)
        signal_tokens = len(signal_text) / CHARS_PER_TOKEN
        signal_ratio = signal_tokens / raw_tokens if raw_tokens > 0 else 0

        if signal_ratio < POOR_SIGNAL_RATIO:
            deductions += 0.25
            findings.append(
                f"Signal-to-noise ratio is {signal_ratio:.0%} — most of the page is noise"
            )
        elif signal_ratio < GOOD_SIGNAL_RATIO:
            deductions += 0.10
            findings.append(
                f"Signal-to-noise ratio is {signal_ratio:.0%} — room for improvement"
            )
        else:
            findings.append(
                f"Signal-to-noise ratio is {signal_ratio:.0%} — good content density"
            )

        # 3. Inline script/style bloat
        script_style_size = self._measure_inline_bloat(soup)
        bloat_ratio = script_style_size / len(raw_html) if raw_html else 0

        if bloat_ratio > 0.50:
            deductions += 0.20
            findings.append(
                f"Inline scripts/styles are {bloat_ratio:.0%} of page — massive bloat"
            )
        elif bloat_ratio > 0.25:
            deductions += 0.10
            findings.append(
                f"Inline scripts/styles are {bloat_ratio:.0%} of page — significant bloat"
            )
        else:
            findings.append(
                f"Inline scripts/styles are {bloat_ratio:.0%} of page — reasonable"
            )

        # 4. DOM depth (deep nesting = more tokens for structure)
        max_depth = self._max_dom_depth(soup)
        if max_depth > 25:
            deductions += 0.10
            findings.append(f"Max DOM depth is {max_depth} — deeply nested structure")
        elif max_depth > 15:
            deductions += 0.05
            findings.append(f"Max DOM depth is {max_depth} — moderately nested")
        else:
            findings.append(f"Max DOM depth is {max_depth} — clean structure")

        # 5. Class attribute bloat (utility-first CSS = lots of tokens)
        class_tokens = self._measure_class_bloat(soup)
        class_ratio = class_tokens / raw_tokens if raw_tokens > 0 else 0

        if class_ratio > 0.15:
            deductions += 0.15
            findings.append(
                f"CSS class attributes consume ~{class_tokens:,.0f} tokens "
                f"({class_ratio:.0%} of page) — utility class bloat"
            )
        elif class_ratio > 0.05:
            deductions += 0.05
            findings.append(
                f"CSS class attributes consume ~{class_tokens:,.0f} tokens ({class_ratio:.0%} of page)"
            )

        # 6. Dollar cost estimates
        cost_per_page = {
            model: (raw_tokens / 1_000_000) * price
            for model, price in MODEL_PRICING.items()
        }
        # Estimate for a 5-page agent session
        session_cost = {model: cost * 5 for model, cost in cost_per_page.items()}
        cheapest = min(cost_per_page.values())
        most_expensive = max(cost_per_page.values())
        if most_expensive > 0.50:
            findings.append(
                f"Reading this page costs ${cheapest:.2f}–${most_expensive:.2f} per load "
                f"(${min(session_cost.values()):.2f}–${max(session_cost.values()):.2f} for a 5-page session)"
            )
        elif most_expensive > 0.05:
            findings.append(
                f"Page read cost: ${cheapest:.3f}–${most_expensive:.3f} per load"
            )
        else:
            findings.append("Page read cost: <$0.05 per load — affordable")

        # 7. Check if common internal links exist (navigation cost proxy)
        internal_links = self._count_internal_links(soup)
        if internal_links > 100:
            deductions += 0.05
            findings.append(
                f"{internal_links} internal links — agents may waste tokens exploring"
            )

        details = {
            "raw_tokens": int(raw_tokens),
            "signal_tokens": int(signal_tokens),
            "signal_ratio": round(signal_ratio, 3),
            "max_dom_depth": max_depth,
            "class_token_ratio": round(class_ratio, 3),
            "inline_bloat_ratio": round(bloat_ratio, 3),
            "cost_per_page_usd": {k: round(v, 4) for k, v in cost_per_page.items()},
            "cost_5_pages_usd": {k: round(v, 4) for k, v in session_cost.items()},
            "internal_links": internal_links,
        }

        score = max(0.0, min(1.0, 1.0 - deductions))
        return CheckResult(
            name=self.name, score=score, findings=findings, details=details
        )

    def _compute_signal_noise(
        self, soup: BeautifulSoup, raw_html: str
    ) -> tuple[str, int]:
        """Extract meaningful text content vs noise.

        Returns (signal_text, noise_byte_count).
        """
        # Remove noise elements
        for tag in soup.find_all(NOISE_TAGS):
            tag.decompose()

        # Remove comments
        for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
            comment.extract()

        # Get remaining text
        signal_text = soup.get_text(separator=" ", strip=True)
        # Collapse whitespace
        signal_text = re.sub(r"\s+", " ", signal_text).strip()

        noise_size = len(raw_html) - len(signal_text)
        return signal_text, noise_size

    def _measure_inline_bloat(self, soup: BeautifulSoup) -> int:
        """Measure total size of inline <script> and <style> content."""
        # Need to re-parse since _compute_signal_noise decomposed elements
        soup2 = BeautifulSoup(str(soup), "html.parser")
        total = 0
        for tag in soup2.find_all(["script", "style"]):
            if tag.string:
                total += len(tag.string)
        return total

    def _max_dom_depth(self, soup: BeautifulSoup) -> int:
        """Find the maximum nesting depth in the DOM."""

        def _depth(element: object, current: int = 0) -> int:
            max_d = current
            children = getattr(element, "children", None)
            if children is None:
                return max_d
            for child in children:
                if hasattr(child, "children"):
                    max_d = max(max_d, _depth(child, current + 1))
            return max_d

        return _depth(soup)

    def _count_internal_links(self, soup: BeautifulSoup) -> int:
        """Count internal (same-domain) links on the page."""
        from urllib.parse import urlparse

        base_domain = urlparse(self.url).netloc
        count = 0
        for a in soup.find_all("a", href=True):
            href = str(a["href"])
            if href.startswith("/") or href.startswith("#"):
                count += 1
            else:
                parsed = urlparse(href)
                if parsed.netloc == base_domain or not parsed.netloc:
                    count += 1
        return count

    def _measure_class_bloat(self, soup: BeautifulSoup) -> float:
        """Estimate tokens consumed by class attributes."""
        total_chars = 0
        for tag in soup.find_all(True):
            classes = tag.get("class")
            if classes and isinstance(classes, list):
                total_chars += len(" ".join(str(c) for c in classes))
        return total_chars / CHARS_PER_TOKEN
