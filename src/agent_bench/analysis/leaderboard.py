"""Generate a standalone HTML leaderboard comparing multiple site analyses."""

from __future__ import annotations

import json
from pathlib import Path


def _score_color(score: float) -> str:
    if score >= 0.7:
        return "#4ade80"
    elif score >= 0.4:
        return "#fbbf24"
    else:
        return "#f87171"


def _bar(score: float, width: int = 60) -> str:
    filled = int(score * width)
    color = _score_color(score)
    return f'<span style="display:inline-block;width:{width}px;height:8px;background:rgba(255,255,255,0.1);border-radius:4px;vertical-align:middle;margin-right:6px"><span style="display:block;width:{filled}px;height:8px;background:{color};border-radius:4px"></span></span>'


def _build_findings_html(result: dict) -> str:
    """Build HTML for the expandable findings detail row."""
    parts = []
    for check in result.get("checks", []):
        name = check["name"]
        score = check["score"]
        findings = check.get("findings", [])
        if not findings:
            continue
        items = "".join(f"<li>{f}</li>" for f in findings)
        parts.append(
            f"<div class='finding-group'>"
            f"<strong style='color:{_score_color(score)}'>{name.title()} ({score:.0%})</strong>"
            f"<ul>{items}</ul></div>"
        )
    return "".join(parts) if parts else "<em>No findings</em>"


def load_results(paths: list[Path]) -> list[dict]:
    """Load and sort result files by overall score descending."""
    results = []
    for p in paths:
        with open(p) as f:
            data = json.load(f)
        # Handle both single results and arrays (e.g. summary.json)
        if isinstance(data, list):
            results.extend(data)
        elif isinstance(data, dict):
            results.append(data)
    results.sort(key=lambda r: r.get("overall_score", 0), reverse=True)
    return results


def _extract_check_scores(result: dict) -> dict[str, float]:
    """Extract check name -> score mapping."""
    scores = {}
    for check in result.get("checks", []):
        scores[check["name"]] = check["score"]
    return scores


def render_leaderboard(results: list[dict]) -> str:
    """Render an HTML leaderboard from a list of result dicts."""
    # Collect all check names across all results
    all_checks: list[str] = []
    for r in results:
        for check in r.get("checks", []):
            if check["name"] not in all_checks:
                all_checks.append(check["name"])

    # Build table rows
    rows = []
    for i, r in enumerate(results):
        url = r.get("url", "unknown")
        # Clean up URL for display
        display = url.replace("https://", "").replace("http://", "").rstrip("/")
        overall = r.get("overall_score", 0)
        check_scores = _extract_check_scores(r)

        cells = [
            f"<td style='color:rgba(255,255,255,0.5)'>{i+1}</td>",
            f"<td><a href='{url}' style='color:#fff;text-decoration:none'>{display}</a></td>",
            f"<td>{_bar(overall)}<span style='color:{_score_color(overall)}'>{overall:.0%}</span></td>",
        ]
        for check_name in all_checks:
            s = check_scores.get(check_name, 0)
            cells.append(f"<td style='color:{_score_color(s)}'>{s:.0%}</td>")

        row_id = f"detail-{i}"
        rows.append(f"<tr class='clickable' onclick=\"toggleDetail('{row_id}')\">{''.join(cells)}</tr>")

        # Build detail row with findings
        findings_html = _build_findings_html(r)
        col_span = 3 + len(all_checks)
        rows.append(
            f"<tr id='{row_id}' class='detail-row' style='display:none'>"
            f"<td colspan='{col_span}'>{findings_html}</td></tr>"
        )

    # Header
    check_headers = "".join(
        f"<th>{name.title()}</th>" for name in all_checks
    )

    count = len(results)
    avg = sum(r.get("overall_score", 0) for r in results) / count if count else 0
    top = results[0].get("url", "").replace("https://", "").rstrip("/") if results else "—"
    bottom = results[-1].get("url", "").replace("https://", "").rstrip("/") if results else "—"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>agent-bench Leaderboard</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: 'Inter', system-ui, sans-serif;
    background: #0a0f1a;
    color: #fff;
    min-height: 100vh;
    padding: 40px 20px;
}}
.container {{ max-width: 1100px; margin: 0 auto; }}
h1 {{ font-size: 1.8rem; font-weight: 600; margin-bottom: 0.5rem; }}
.subtitle {{ color: rgba(255,255,255,0.5); margin-bottom: 2rem; font-size: 0.95rem; }}
.stats {{
    display: flex; gap: 24px; margin-bottom: 2rem;
    flex-wrap: wrap;
}}
.stat {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 16px 20px;
    min-width: 160px;
}}
.stat-label {{ font-size: 0.75rem; color: rgba(255,255,255,0.4); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }}
.stat-value {{ font-size: 1.4rem; font-weight: 600; }}
table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.88rem;
}}
th {{
    text-align: left;
    padding: 10px 12px;
    color: rgba(255,255,255,0.4);
    font-weight: 500;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}}
td {{
    padding: 10px 12px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
}}
tr:hover td {{ background: rgba(255,255,255,0.03); }}
tr.clickable {{ cursor: pointer; }}
tr.clickable:hover td {{ background: rgba(255,255,255,0.06); }}
.detail-row td {{
    padding: 16px 20px;
    background: rgba(255,255,255,0.02);
    border-bottom: 1px solid rgba(255,255,255,0.08);
}}
.finding-group {{
    display: inline-block;
    vertical-align: top;
    width: 280px;
    margin: 0 16px 12px 0;
}}
.finding-group ul {{
    margin: 4px 0 0 16px;
    color: rgba(255,255,255,0.6);
    font-size: 0.82rem;
    line-height: 1.5;
}}
.finding-group li {{ margin-bottom: 2px; }}
.footer {{
    margin-top: 2rem;
    color: rgba(255,255,255,0.3);
    font-size: 0.8rem;
}}
@media (max-width: 768px) {{
    table {{ font-size: 0.78rem; }}
    th, td {{ padding: 8px 6px; }}
    .stats {{ gap: 12px; }}
}}
</style>
</head>
<body>
<div class="container">
    <h1>🏆 Agent-Readiness Leaderboard</h1>
    <p class="subtitle">Scored by <a href="https://github.com/LightLayer-dev/agent-bench" style="color:rgba(255,255,255,0.6)">agent-bench</a> static analysis</p>

    <div class="stats">
        <div class="stat">
            <div class="stat-label">Sites Analyzed</div>
            <div class="stat-value">{count}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Average Score</div>
            <div class="stat-value" style="color:{_score_color(avg)}">{avg:.0%}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Top Site</div>
            <div class="stat-value" style="font-size:1rem">{top}</div>
        </div>
        <div class="stat">
            <div class="stat-label">Bottom Site</div>
            <div class="stat-value" style="font-size:1rem">{bottom}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Site</th>
                <th>Overall</th>
                {check_headers}
            </tr>
        </thead>
        <tbody>
            {''.join(rows)}
        </tbody>
    </table>

    <p class="footer">Generated by agent-bench · Static analysis only · No LLM calls · Click a row for details</p>
</div>
<script>
function toggleDetail(id) {{
    var el = document.getElementById(id);
    el.style.display = el.style.display === 'none' ? 'table-row' : 'none';
}}
</script>
</body>
</html>"""
    return html
