"""Tests for the accessibility (a11y) check."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from agent_bench.analysis.checks.a11y import A11yCheck


def _mock_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    resp.status_code = 200
    return resp


def _run_check(html: str) -> dict:
    with patch("agent_bench.analysis.checks.a11y.httpx.get", return_value=_mock_response(html)):
        check = A11yCheck(url="http://example.com")
        result = check.execute()
        return {"score": result.score, "findings": result.findings, "details": result.details}


class TestLandmarks:
    def test_full_landmarks(self):
        html = '<html><body><header>H</header><nav>N</nav><main>M</main><footer>F</footer></body></html>'
        r = _run_check(html)
        assert r["details"]["landmark_count"] >= 4
        assert r["score"] > 0

    def test_no_landmarks(self):
        html = '<html><body><div>Hello</div></body></html>'
        r = _run_check(html)
        assert r["details"]["landmark_count"] == 0
        assert any("No landmark" in f for f in r["findings"])

    def test_explicit_role_landmarks(self):
        html = '<html><body><div role="main">M</div><div role="navigation">N</div></body></html>'
        r = _run_check(html)
        assert "main" in r["details"]["landmarks_found"]
        assert "navigation" in r["details"]["landmarks_found"]

    def test_mixed_implicit_explicit(self):
        html = '<html><body><nav>N</nav><div role="main">M</div><div role="search">S</div></body></html>'
        r = _run_check(html)
        assert r["details"]["landmark_count"] >= 3


class TestAltText:
    def test_all_images_have_alt(self):
        html = '<html><body><img src="a.png" alt="photo"><img src="b.png" alt=""></body></html>'
        r = _run_check(html)
        assert r["details"]["images_missing_alt"] == 0
        assert r["details"]["images_with_alt"] == 1
        assert r["details"]["images_decorative"] == 1

    def test_missing_alt(self):
        html = '<html><body><img src="a.png"><img src="b.png" alt="ok"></body></html>'
        r = _run_check(html)
        assert r["details"]["images_missing_alt"] == 1
        assert any("missing alt" in f for f in r["findings"])

    def test_no_images(self):
        html = '<html><body><p>No images here</p></body></html>'
        r = _run_check(html)
        assert r["details"]["images_total"] == 0


class TestSkipLinks:
    def test_skip_link_found(self):
        html = '<html><body><a href="#main">Skip to main content</a><main id="main">Content</main></body></html>'
        r = _run_check(html)
        assert len(r["details"]["skip_links"]) == 1

    def test_no_skip_links(self):
        html = '<html><body><a href="/about">About</a><main>Content</main></body></html>'
        r = _run_check(html)
        assert len(r["details"]["skip_links"]) == 0


class TestLiveRegions:
    def test_aria_live_found(self):
        html = '<html><body><div aria-live="polite">Updates here</div></body></html>'
        r = _run_check(html)
        assert r["details"]["live_regions"] >= 1

    def test_status_role(self):
        html = '<html><body><div role="status">Loading...</div></body></html>'
        r = _run_check(html)
        assert r["details"]["live_regions"] >= 1

    def test_no_live_regions(self):
        html = '<html><body><div>Static</div></body></html>'
        r = _run_check(html)
        assert r["details"]["live_regions"] == 0


class TestFocusManagement:
    def test_positive_tabindex_penalized(self):
        html = '<html><body><button tabindex="1">First</button><button tabindex="2">Second</button></body></html>'
        r = _run_check(html)
        assert r["details"]["tabindex_positive"] == 2

    def test_zero_tabindex_rewarded(self):
        html = '<html><body><div tabindex="0">Focusable</div></body></html>'
        r = _run_check(html)
        assert r["details"]["tabindex_zero"] == 1

    def test_no_tabindex(self):
        html = '<html><body><button>Click</button></body></html>'
        r = _run_check(html)
        assert r["details"]["tabindex_positive"] == 0
        assert r["details"]["tabindex_zero"] == 0


class TestOverallScore:
    def test_well_accessible_page(self):
        html = '''<html><body>
            <a href="#main">Skip to content</a>
            <header><nav>Nav</nav></header>
            <main id="main">
                <img src="photo.jpg" alt="A photo">
                <div aria-live="polite">Status</div>
                <div tabindex="0">Custom widget</div>
            </main>
            <footer>Footer</footer>
        </body></html>'''
        r = _run_check(html)
        assert r["score"] >= 0.7

    def test_inaccessible_page(self):
        html = '<html><body><div><img src="x.png"><img src="y.png"></div></body></html>'
        r = _run_check(html)
        assert r["score"] < 0.4
