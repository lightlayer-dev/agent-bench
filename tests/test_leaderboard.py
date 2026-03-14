"""Tests for leaderboard HTML generation."""

import json
from agent_bench.analysis.leaderboard import load_results, render_leaderboard, _score_color


class TestScoreColor:
    def test_green(self):
        assert _score_color(0.8) == "#4ade80"

    def test_amber(self):
        assert _score_color(0.5) == "#fbbf24"

    def test_red(self):
        assert _score_color(0.2) == "#f87171"

    def test_boundary_green(self):
        assert _score_color(0.7) == "#4ade80"

    def test_boundary_amber(self):
        assert _score_color(0.4) == "#fbbf24"


def _make_result(url: str, score: float, checks: list[dict] | None = None) -> dict:
    return {
        "url": url,
        "overall_score": score,
        "checks": checks or [
            {"name": "api", "score": score, "findings": []},
            {"name": "docs", "score": score, "findings": []},
        ],
    }


class TestLoadResults:
    def test_loads_and_sorts(self, tmp_path):
        (tmp_path / "a.json").write_text(json.dumps(_make_result("https://a.com", 0.3)))
        (tmp_path / "b.json").write_text(json.dumps(_make_result("https://b.com", 0.8)))
        results = load_results([tmp_path / "a.json", tmp_path / "b.json"])
        assert len(results) == 2
        assert results[0]["url"] == "https://b.com"
        assert results[1]["url"] == "https://a.com"

    def test_single_file(self, tmp_path):
        (tmp_path / "x.json").write_text(json.dumps(_make_result("https://x.com", 0.5)))
        results = load_results([tmp_path / "x.json"])
        assert len(results) == 1


class TestRenderLeaderboard:
    def test_renders_valid_html(self):
        results = [
            _make_result("https://good.com", 0.75),
            _make_result("https://bad.com", 0.25),
        ]
        html = render_leaderboard(results)
        assert "<!DOCTYPE html>" in html
        assert "good.com" in html
        assert "bad.com" in html
        assert "75%" in html
        assert "25%" in html

    def test_contains_stats(self):
        results = [
            _make_result("https://top.com", 0.9),
            _make_result("https://bottom.com", 0.1),
        ]
        html = render_leaderboard(results)
        assert "top.com" in html
        assert "bottom.com" in html
        assert "Sites Analyzed" in html
        assert "2" in html  # count

    def test_check_columns(self):
        results = [
            _make_result("https://x.com", 0.5, [
                {"name": "api", "score": 0.8, "findings": []},
                {"name": "structure", "score": 0.3, "findings": []},
            ]),
        ]
        html = render_leaderboard(results)
        assert "Api" in html
        assert "Structure" in html
        assert "80%" in html
        assert "30%" in html

    def test_empty_results(self):
        html = render_leaderboard([])
        assert "<!DOCTYPE html>" in html
        assert "0" in html  # count

    def test_clickable_rows(self):
        results = [_make_result("https://x.com", 0.5)]
        html = render_leaderboard(results)
        assert "toggleDetail" in html
        assert "clickable" in html
        assert "detail-0" in html

    def test_findings_in_detail(self):
        results = [
            _make_result("https://x.com", 0.5, [
                {"name": "api", "score": 0.8, "findings": ["Found 5 endpoints"]},
            ]),
        ]
        html = render_leaderboard(results)
        assert "Found 5 endpoints" in html

    def test_ranking_order(self):
        results = [
            _make_result("https://alpha.com", 0.9),
            _make_result("https://beta.com", 0.5),
            _make_result("https://gamma.com", 0.1),
        ]
        html = render_leaderboard(results)
        # Find positions in the table body (after <tbody>)
        tbody = html[html.index("<tbody>"):]
        alpha_pos = tbody.index("alpha.com")
        beta_pos = tbody.index("beta.com")
        gamma_pos = tbody.index("gamma.com")
        assert alpha_pos < beta_pos < gamma_pos
