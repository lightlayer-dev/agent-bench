"""Site classifier — detect what kind of website this is."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import httpx
from bs4 import BeautifulSoup


class SiteCategory(str, Enum):
    """High-level website categories."""
    ECOMMERCE = "ecommerce"
    SAAS = "saas"
    DOCUMENTATION = "documentation"
    SOCIAL = "social"
    NEWS_MEDIA = "news_media"
    GOVERNMENT = "government"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    SEARCH = "search"
    API_SERVICE = "api_service"
    GENERIC = "generic"


@dataclass
class SiteProfile:
    """Profile of a classified website."""
    url: str
    category: SiteCategory
    confidence: float  # 0.0 - 1.0
    signals: list[str] = field(default_factory=list)
    features: dict[str, bool] = field(default_factory=dict)

    @property
    def has_search(self) -> bool:
        return self.features.get("search", False)

    @property
    def has_auth(self) -> bool:
        return self.features.get("auth", False)

    @property
    def has_forms(self) -> bool:
        return self.features.get("forms", False)

    @property
    def has_cart(self) -> bool:
        return self.features.get("cart", False)


# Keyword signals for each category
_CATEGORY_SIGNALS: dict[SiteCategory, list[str]] = {
    SiteCategory.ECOMMERCE: [
        "add to cart", "add to bag", "buy now", "checkout", "shopping cart",
        "price", "product", "shop", "store", "wishlist", "add-to-cart",
        "shopify", "woocommerce", "bigcommerce", "magento",
    ],
    SiteCategory.SAAS: [
        "sign up", "free trial", "pricing", "dashboard", "get started",
        "api key", "workspace", "team", "plan", "subscription", "upgrade",
    ],
    SiteCategory.DOCUMENTATION: [
        "docs", "documentation", "api reference", "getting started",
        "guide", "tutorial", "changelog", "sdk", "endpoints",
        "mintlify", "readme", "gitbook", "docusaurus",
    ],
    SiteCategory.SOCIAL: [
        "profile", "follow", "post", "feed", "timeline", "like",
        "comment", "share", "notification", "message",
    ],
    SiteCategory.NEWS_MEDIA: [
        "article", "breaking news", "subscribe", "newsletter",
        "author", "published", "byline", "opinion", "editorial",
    ],
    SiteCategory.FINANCE: [
        "account balance", "transfer", "payment", "banking",
        "portfolio", "investment", "stock", "trading", "transaction",
    ],
    SiteCategory.SEARCH: [
        "search results", "web search", "image search",
    ],
    SiteCategory.API_SERVICE: [
        "api", "endpoint", "webhook", "rate limit", "authentication",
        "rest api", "graphql", "openapi", "swagger",
    ],
}


class SiteClassifier:
    """Classify a website into a category based on content analysis."""

    def classify(self, url: str) -> SiteProfile:
        """Fetch the site and classify it."""
        try:
            resp = httpx.get(url, follow_redirects=True, timeout=15)
            html = resp.text
        except httpx.HTTPError as e:
            return SiteProfile(
                url=url, category=SiteCategory.GENERIC,
                confidence=0.0, signals=[f"Failed to fetch: {e}"],
            )

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ", strip=True).lower()
        html_lower = html.lower()

        # Score each category
        scores: dict[SiteCategory, float] = {}
        matched_signals: dict[SiteCategory, list[str]] = {}

        for category, keywords in _CATEGORY_SIGNALS.items():
            matches = [kw for kw in keywords if kw in text or kw in html_lower]
            scores[category] = len(matches) / len(keywords)
            matched_signals[category] = matches

        # Detect features
        features = self._detect_features(soup, html_lower)

        # Boost scores based on features
        if features.get("cart"):
            scores[SiteCategory.ECOMMERCE] = scores.get(SiteCategory.ECOMMERCE, 0) + 0.3
        if features.get("search") and not features.get("auth"):
            scores[SiteCategory.SEARCH] = scores.get(SiteCategory.SEARCH, 0) + 0.1

        # Pick the winner
        best = max(scores, key=lambda k: scores[k])
        best_score = scores[best]

        if best_score < 0.1:
            return SiteProfile(
                url=url, category=SiteCategory.GENERIC,
                confidence=0.0, signals=["No strong category signals detected"],
                features=features,
            )

        return SiteProfile(
            url=url, category=best,
            confidence=min(best_score, 1.0),
            signals=matched_signals.get(best, []),
            features=features,
        )

    def _detect_features(self, soup: BeautifulSoup, html: str) -> dict[str, bool]:
        """Detect common website features."""
        features: dict[str, bool] = {}

        # Search
        search_inputs = soup.find_all("input", attrs={"type": "search"})
        search_forms = soup.find_all("form", attrs={"role": "search"})
        search_by_name = soup.find_all("input", attrs={"name": lambda n: n and "search" in n.lower() if n else False})
        features["search"] = bool(search_inputs or search_forms or search_by_name)

        # Auth / Login
        password_inputs = soup.find_all("input", attrs={"type": "password"})
        login_links = soup.find_all("a", string=lambda s: s and any(w in s.lower() for w in ("log in", "login", "sign in", "signin")) if s else False)
        features["auth"] = bool(password_inputs or login_links)

        # Forms (non-search, non-login)
        all_forms = soup.find_all("form")
        features["forms"] = len(all_forms) > 0

        # Cart / E-commerce
        cart_indicators = ["cart", "basket", "bag"]
        features["cart"] = any(ind in html for ind in cart_indicators)

        # Navigation
        nav = soup.find_all("nav")
        features["navigation"] = len(nav) > 0

        # Pagination
        features["pagination"] = bool(
            soup.find("nav", attrs={"aria-label": lambda v: v and "pag" in v.lower() if v else False})
            or soup.find(class_=lambda c: c and "pagination" in c if c else False)
            or "next page" in html
        )

        return features
