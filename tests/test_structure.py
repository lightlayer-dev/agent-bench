"""Tests for the structure analysis check."""

from unittest.mock import patch, MagicMock
from bs4 import BeautifulSoup

from agent_bench.analysis.checks.structure import StructureCheck


def _make_check(url: str = "https://example.com") -> StructureCheck:
    return StructureCheck(url=url)


class TestSemanticHTML:
    def test_good_semantic_html(self):
        check = _make_check()
        html = "<html><body><nav>Nav</nav><main><article><section>Content</section></article></main><footer>F</footer></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_semantic_html(soup, details)
        assert score > 0.5
        assert details["semantic_count"] >= 4

    def test_div_soup(self):
        check = _make_check()
        html = "<html><body>" + "<div>block</div>" * 20 + "</body></html>"
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_semantic_html(soup, details)
        assert score == 0.0
        assert "No semantic HTML" in findings[0]

    def test_empty_page(self):
        check = _make_check()
        soup = BeautifulSoup("", "html.parser")
        details: dict = {}
        score, findings = check._check_semantic_html(soup, details)
        assert score == 0.0


class TestAriaLabels:
    def test_labeled_buttons(self):
        check = _make_check()
        html = '<button aria-label="Submit">Submit</button><a href="/" title="Home">Home</a>'
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_aria_labels(soup, details)
        assert score == 1.0

    def test_unlabeled_inputs(self):
        check = _make_check()
        html = '<input type="text"><input type="password"><button></button>'
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_aria_labels(soup, details)
        assert score < 1.0


class TestSSR:
    def test_ssr_detected(self):
        check = _make_check()
        html = "<html><body><main>" + "Content " * 200 + "</main></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_ssr(soup, details)
        assert score == 1.0
        assert details["rendering"] == "server-side"

    def test_spa_detected(self):
        check = _make_check()
        html = '<html><body><div id="root"></div><script>app.mount()</script></body></html>'
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_ssr(soup, details)
        assert score <= 0.3
        assert details["rendering"] in ("client-side", "minimal")


class TestStableSelectors:
    def test_with_testids(self):
        check = _make_check()
        html = '<button data-testid="submit">Go</button><div data-cy="header">H</div>' * 6
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_stable_selectors(soup, details)
        assert score >= 1.0

    def test_no_testids(self):
        check = _make_check()
        html = "<div><span>Hello</span></div>"
        soup = BeautifulSoup(html, "html.parser")
        details: dict = {}
        score, findings = check._check_stable_selectors(soup, details)
        assert score == 0.0
