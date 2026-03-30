"""Generate a standalone HTML report for site analysis results."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_bench.analysis.report import AnalysisReport
    from agent_bench.analysis.models import CheckResult


def _score_color(score: float) -> str:
    """Return a CSS color for a score value."""
    if score >= 0.7:
        return "#4ade80"  # green
    elif score >= 0.4:
        return "#fbbf24"  # amber
    else:
        return "#f87171"  # red


def _score_label(score: float) -> str:
    if score >= 0.7:
        return "Good"
    elif score >= 0.4:
        return "Moderate"
    else:
        return "Poor"


def _bar_html(score: float, width: int = 200) -> str:
    """Render a score bar as inline HTML."""
    filled = int(score * width)
    color = _score_color(score)
    return (
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'<div style="width:{width}px;height:8px;background:rgba(255,255,255,0.1);border-radius:4px;overflow:hidden;">'
        f'<div style="width:{filled}px;height:100%;background:{color};border-radius:4px;"></div>'
        f"</div>"
        f'<span style="color:{color};font-weight:600;font-size:0.95rem;">{score:.0%}</span>'
        f"</div>"
    )


def _check_card_html(result: CheckResult) -> str:
    """Render a single check result as an HTML card."""
    color = _score_color(result.score)
    findings_html = ""
    for finding in result.findings:
        findings_html += f'<li style="margin-bottom:6px;color:rgba(255,255,255,0.7);font-size:0.9rem;">{finding}</li>'

    return f"""
    <div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.08);border-radius:8px;padding:20px 24px;margin-bottom:16px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;">
            <h3 style="margin:0;font-size:1.1rem;font-weight:500;color:#fff;text-transform:capitalize;">{result.name}</h3>
            <span style="color:{color};font-weight:600;font-size:1.1rem;">{result.score:.0%}</span>
        </div>
        {_bar_html(result.score)}
        <ul style="margin:12px 0 0 16px;padding:0;list-style:none;">
            {findings_html}
        </ul>
    </div>
    """


def render_html_report(report: AnalysisReport) -> str:
    """Render a complete analysis report as a standalone HTML page."""
    overall_color = _score_color(report.overall_score)
    overall_label = _score_label(report.overall_score)

    checks_html = ""
    for result in report.check_results:
        checks_html += _check_card_html(result)

    # Weight labels

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Agent-Readiness Report — {report.url}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            line-height: 1.6;
            color: #ffffff;
            background: #0a0f1a;
            min-height: 100vh;
            padding: 40px 20px;
        }}
        .container {{ max-width: 720px; margin: 0 auto; }}
        .header {{ text-align: center; margin-bottom: 40px; }}
        .header h1 {{ font-size: 1.8rem; font-weight: 600; margin-bottom: 8px; }}
        .header .url {{ color: rgba(255,255,255,0.5); font-size: 0.95rem; word-break: break-all; }}
        .overall {{
            text-align: center;
            padding: 32px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            margin-bottom: 32px;
        }}
        .overall .score {{
            font-size: 4rem;
            font-weight: 700;
            color: {overall_color};
            line-height: 1;
        }}
        .overall .label {{
            font-size: 1.1rem;
            color: {overall_color};
            margin-top: 8px;
            font-weight: 500;
        }}
        .overall .subtitle {{
            color: rgba(255,255,255,0.4);
            font-size: 0.85rem;
            margin-top: 4px;
        }}
        .section-title {{
            font-size: 1.1rem;
            font-weight: 600;
            margin-bottom: 16px;
            color: rgba(255,255,255,0.6);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.08);
            color: rgba(255,255,255,0.3);
            font-size: 0.8rem;
        }}
        .footer a {{ color: rgba(255,255,255,0.5); text-decoration: underline; }}
        @media (max-width: 600px) {{
            .overall .score {{ font-size: 3rem; }}
            .header h1 {{ font-size: 1.4rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Agent-Readiness Report</h1>
            <p class="url">{report.url}</p>
        </div>

        <div class="overall">
            <div class="score">{report.overall_score:.0%}</div>
            <div class="label">{overall_label}</div>
            <div class="subtitle">Weighted score across {len(report.check_results)} dimensions</div>
        </div>

        <div class="section-title">Breakdown</div>
        {checks_html}

        <div class="footer">
            Generated by <a href="https://github.com/lightlayer-dev/agent-bench">agent-bench</a> · LightLayer
        </div>
    </div>
</body>
</html>"""
