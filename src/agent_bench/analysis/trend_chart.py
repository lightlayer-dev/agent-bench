"""HTML trend chart rendering with inline SVG."""

from __future__ import annotations

from agent_bench.analysis.trend import SiteTrend, TrendStore


def _svg_sparkline(values: list[float], width: int = 400, height: int = 80, color: str = "#4fc3f7") -> str:
    """Generate an SVG sparkline from a list of values (0-1 range)."""
    if not values:
        return ""
    if len(values) == 1:
        # Single dot
        cx = width // 2
        cy = height - int(values[0] * (height - 10)) - 5
        return f'<svg width="{width}" height="{height}"><circle cx="{cx}" cy="{cy}" r="4" fill="{color}"/></svg>'

    n = len(values)
    points: list[str] = []
    dots: list[str] = []
    for i, v in enumerate(values):
        x = int(i * (width - 10) / (n - 1)) + 5
        y = height - int(v * (height - 10)) - 5
        points.append(f"{x},{y}")
        dots.append(f'<circle cx="{x}" cy="{y}" r="3" fill="{color}"/>')

    polyline = f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2"/>'
    return f'<svg width="{width}" height="{height}">{polyline}{"".join(dots)}</svg>'


def _direction_badge(direction: str) -> str:
    """HTML badge for trend direction."""
    colors = {"▲": "#4caf50", "▼": "#f44336", "=": "#9e9e9e", "—": "#616161"}
    color = colors.get(direction, "#616161")
    return f'<span style="color:{color};font-weight:bold;font-size:1.2em">{direction}</span>'


def render_trend_html(trend: SiteTrend) -> str:
    """Render a single site's trend as standalone HTML."""
    scores = [s.overall_score for s in trend.snapshots]
    sparkline = _svg_sparkline(scores)

    # Per-check sparklines
    check_names = sorted({k for s in trend.snapshots for k in s.check_scores})
    check_rows = ""
    for check in check_names:
        check_values = [s.check_scores.get(check, 0) for s in trend.snapshots]
        check_spark = _svg_sparkline(check_values, width=300, height=50, color="#81d4fa")
        latest = check_values[-1] if check_values else 0
        delta = trend.check_delta(check)
        delta_str = ""
        if delta is not None:
            sign = "+" if delta > 0 else ""
            color = "#4caf50" if delta > 0.01 else "#f44336" if delta < -0.01 else "#9e9e9e"
            delta_str = f'<span style="color:{color}">{sign}{delta:.0%}</span>'
        check_rows += f"""
        <tr>
            <td style="padding:8px;font-weight:bold">{check}</td>
            <td style="padding:8px">{latest:.0%}</td>
            <td style="padding:8px">{delta_str}</td>
            <td style="padding:8px">{check_spark}</td>
        </tr>"""

    # Timeline entries
    timeline = ""
    for i, snap in enumerate(trend.snapshots):
        dt_str = snap.dt.strftime("%Y-%m-%d %H:%M UTC")
        prev_score = trend.snapshots[i - 1].overall_score if i > 0 else None
        change = ""
        if prev_score is not None:
            d = snap.overall_score - prev_score
            sign = "+" if d > 0 else ""
            color = "#4caf50" if d > 0.01 else "#f44336" if d < -0.01 else "#9e9e9e"
            change = f' <span style="color:{color}">({sign}{d:.0%})</span>'
        timeline += f'<div style="padding:4px 0">{dt_str} — <strong>{snap.overall_score:.0%}</strong>{change}</div>'

    delta_str = ""
    if trend.delta is not None:
        sign = "+" if trend.delta > 0 else ""
        delta_str = f"{sign}{trend.delta:.0%}"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Trend: {trend.url}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }}
  .container {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ color: #4fc3f7; }}
  .card {{ background: #16213e; border-radius: 12px; padding: 24px; margin: 16px 0; }}
  .score-big {{ font-size: 3em; font-weight: bold; color: #4fc3f7; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 8px; color: #90a4ae; border-bottom: 1px solid #2a3a5e; }}
  tr:hover {{ background: #1a2744; }}
</style>
</head>
<body>
<div class="container">
  <h1>📈 Score Trend</h1>
  <h2>{trend.url}</h2>

  <div class="card">
    <div style="display:flex;align-items:center;gap:20px">
      <div>
        <div class="score-big">{scores[-1] if scores else 0:.0%}</div>
        <div style="color:#90a4ae">Latest Score</div>
      </div>
      <div>
        <div style="font-size:1.5em">{_direction_badge(trend.direction)} {delta_str}</div>
        <div style="color:#90a4ae">{len(trend.snapshots)} snapshots</div>
      </div>
    </div>
    <div style="margin-top:16px">{sparkline}</div>
  </div>

  <div class="card">
    <h3>Per-Check Trends</h3>
    <table>
      <thead><tr><th>Check</th><th>Latest</th><th>Change</th><th>Trend</th></tr></thead>
      <tbody>{check_rows}</tbody>
    </table>
  </div>

  <div class="card">
    <h3>Timeline</h3>
    {timeline}
  </div>

  <div style="text-align:center;color:#616161;margin-top:24px;font-size:0.85em">
    Generated by <a href="https://github.com/LightLayer-dev/agent-bench" style="color:#4fc3f7">agent-bench</a>
  </div>
</div>
</body>
</html>"""


def render_multi_trend_html(store: TrendStore) -> str:
    """Render trends for all tracked sites as a single HTML page."""
    urls = store.all_urls()
    if not urls:
        return "<html><body><p>No trend data available.</p></body></html>"

    rows = ""
    for url in urls:
        trend = store.get_trend(url)
        if not trend.snapshots:
            continue
        scores = [s.overall_score for s in trend.snapshots]
        spark = _svg_sparkline(scores, width=200, height=40)
        latest = scores[-1]
        delta = trend.delta
        delta_str = ""
        if delta is not None:
            sign = "+" if delta > 0 else ""
            color = "#4caf50" if delta > 0.01 else "#f44336" if delta < -0.01 else "#9e9e9e"
            delta_str = f'<span style="color:{color}">{sign}{delta:.0%}</span>'

        rows += f"""
        <tr>
            <td style="padding:8px"><a href="#" style="color:#4fc3f7">{url}</a></td>
            <td style="padding:8px;font-weight:bold">{latest:.0%}</td>
            <td style="padding:8px">{delta_str}</td>
            <td style="padding:8px">{_direction_badge(trend.direction)}</td>
            <td style="padding:8px">{len(trend.snapshots)}</td>
            <td style="padding:8px">{spark}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>agent-bench — Score Trends</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         background: #1a1a2e; color: #e0e0e0; margin: 0; padding: 20px; }}
  .container {{ max-width: 1100px; margin: 0 auto; }}
  h1 {{ color: #4fc3f7; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 10px; color: #90a4ae; border-bottom: 1px solid #2a3a5e; }}
  tr:hover {{ background: #1a2744; }}
</style>
</head>
<body>
<div class="container">
  <h1>📈 agent-bench Score Trends</h1>
  <p style="color:#90a4ae">{len(urls)} sites tracked</p>
  <table>
    <thead><tr><th>Site</th><th>Latest</th><th>Change</th><th>Direction</th><th>Snapshots</th><th>Trend</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <div style="text-align:center;color:#616161;margin-top:24px;font-size:0.85em">
    Generated by <a href="https://github.com/LightLayer-dev/agent-bench" style="color:#4fc3f7">agent-bench</a>
  </div>
</div>
</body>
</html>"""
