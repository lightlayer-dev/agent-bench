"""Tests for site classifier and task generator."""

from unittest.mock import patch, MagicMock

import httpx

from agent_bench.runner.classifier import SiteClassifier, SiteCategory, SiteProfile
from agent_bench.runner.generator import generate_tasks


def _mock_response(text: str = "", status: int = 200) -> httpx.Response:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = text
    return resp


class TestClassifier:
    def test_ecommerce_detection(self):
        html = """<html><body>
            <nav>Shop</nav>
            <div class="product">Widget - $29.99</div>
            <button class="add-to-cart">Add to Cart</button>
            <a href="/cart">Shopping Cart (0)</a>
            <div class="price">$29.99</div>
        </body></html>"""

        classifier = SiteClassifier()
        with patch("httpx.get", return_value=_mock_response(text=html)):
            profile = classifier.classify("https://store.example.com")
        assert profile.category == SiteCategory.ECOMMERCE
        assert profile.features["cart"]

    def test_saas_detection(self):
        html = """<html><body>
            <nav><a href="/pricing">Pricing</a><a href="/dashboard">Dashboard</a></nav>
            <h1>Start your free trial</h1>
            <p>Get your API key and get started in minutes</p>
            <a href="/signup">Sign Up</a>
            <div>Plans start at $10/month</div>
        </body></html>"""

        classifier = SiteClassifier()
        with patch("httpx.get", return_value=_mock_response(text=html)):
            profile = classifier.classify("https://app.example.com")
        assert profile.category == SiteCategory.SAAS

    def test_docs_detection(self):
        html = """<html><body>
            <nav>Documentation</nav>
            <h1>API Reference</h1>
            <h2>Getting Started</h2>
            <p>This guide will walk you through the SDK endpoints</p>
            <h2>Tutorial</h2>
        </body></html>"""

        classifier = SiteClassifier()
        with patch("httpx.get", return_value=_mock_response(text=html)):
            profile = classifier.classify("https://docs.example.com")
        assert profile.category == SiteCategory.DOCUMENTATION

    def test_generic_fallback(self):
        html = "<html><body><h1>Hello World</h1></body></html>"

        classifier = SiteClassifier()
        with patch("httpx.get", return_value=_mock_response(text=html)):
            profile = classifier.classify("https://example.com")
        assert profile.category == SiteCategory.GENERIC

    def test_feature_detection_search(self):
        html = '<html><body><form role="search"><input type="search" name="q"></form></body></html>'

        classifier = SiteClassifier()
        with patch("httpx.get", return_value=_mock_response(text=html)):
            profile = classifier.classify("https://example.com")
        assert profile.features["search"]

    def test_feature_detection_auth(self):
        html = '<html><body><a href="/login">Log in</a></body></html>'

        classifier = SiteClassifier()
        with patch("httpx.get", return_value=_mock_response(text=html)):
            profile = classifier.classify("https://example.com")
        assert profile.features["auth"]

    def test_fetch_failure(self):
        classifier = SiteClassifier()
        with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
            profile = classifier.classify("https://down.example.com")
        assert profile.category == SiteCategory.GENERIC
        assert profile.confidence == 0.0


class TestTaskGenerator:
    def test_ecommerce_tasks(self):
        profile = SiteProfile(
            url="https://store.example.com",
            category=SiteCategory.ECOMMERCE,
            confidence=0.8,
            features={
                "search": True,
                "cart": True,
                "auth": True,
                "forms": True,
                "navigation": True,
                "pagination": False,
            },
        )
        tasks = generate_tasks(profile)

        names = [t.name for t in tasks]
        # Should have universal + ecommerce + feature tasks
        assert "navigate-home" in names
        assert "browse-products" in names
        assert "add-to-cart" in names
        assert "site-search" in names
        assert "find-login" in names
        assert len(tasks) >= 7

    def test_generic_tasks(self):
        profile = SiteProfile(
            url="https://example.com",
            category=SiteCategory.GENERIC,
            confidence=0.0,
            features={
                "search": False,
                "cart": False,
                "auth": False,
                "forms": False,
                "navigation": False,
                "pagination": False,
            },
        )
        tasks = generate_tasks(profile)

        # Should only have universal tasks
        names = [t.name for t in tasks]
        assert "navigate-home" in names
        assert "extract-links" in names
        assert len(tasks) == 2

    def test_saas_tasks(self):
        profile = SiteProfile(
            url="https://app.example.com",
            category=SiteCategory.SAAS,
            confidence=0.7,
            features={
                "search": False,
                "cart": False,
                "auth": True,
                "forms": True,
                "navigation": True,
                "pagination": False,
            },
        )
        tasks = generate_tasks(profile)
        names = [t.name for t in tasks]
        assert "find-pricing" in names
        assert "start-signup-flow" in names

    def test_all_tasks_have_required_fields(self):
        """Every generated task should have name, site, description, and at least one step."""
        for category in SiteCategory:
            profile = SiteProfile(
                url="https://example.com",
                category=category,
                confidence=0.5,
                features={
                    "search": True,
                    "cart": True,
                    "auth": True,
                    "forms": True,
                    "navigation": True,
                    "pagination": True,
                },
            )
            tasks = generate_tasks(profile)
            for task in tasks:
                assert task.name, f"Task missing name for {category}"
                assert task.site, f"Task missing site for {category}"
                assert task.description, f"Task missing description for {category}"
                assert len(task.steps) > 0, (
                    f"Task {task.name} has no steps for {category}"
                )
