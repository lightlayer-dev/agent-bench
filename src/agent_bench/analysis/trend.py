"""Trend tracking — score history over time for sites."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ScoreSnapshot:
    """A single point-in-time score for a site."""

    timestamp: str
    overall_score: float
    check_scores: dict[str, float] = field(default_factory=dict)

    @property
    def dt(self) -> datetime:
        return datetime.fromisoformat(self.timestamp)


@dataclass
class SiteTrend:
    """Score history for a single site."""

    url: str
    snapshots: list[ScoreSnapshot] = field(default_factory=list)

    @property
    def latest(self) -> ScoreSnapshot | None:
        return self.snapshots[-1] if self.snapshots else None

    @property
    def oldest(self) -> ScoreSnapshot | None:
        return self.snapshots[0] if self.snapshots else None

    @property
    def delta(self) -> float | None:
        """Overall score change from oldest to latest."""
        if len(self.snapshots) < 2:
            return None
        return self.snapshots[-1].overall_score - self.snapshots[0].overall_score

    @property
    def direction(self) -> str:
        """▲ improving, ▼ declining, = stable."""
        d = self.delta
        if d is None:
            return "—"
        if d > 0.01:
            return "▲"
        if d < -0.01:
            return "▼"
        return "="

    def check_delta(self, check_name: str) -> float | None:
        """Score change for a specific check."""
        if len(self.snapshots) < 2:
            return None
        before = self.snapshots[0].check_scores.get(check_name)
        after = self.snapshots[-1].check_scores.get(check_name)
        if before is None or after is None:
            return None
        return after - before


class TrendStore:
    """Persistent store for score history, backed by a JSON file."""

    def __init__(self, path: Path | str = "trend-history.json") -> None:
        self.path = Path(path)
        self._data: dict[str, list[dict]] = {}
        if self.path.exists():
            self._data = json.loads(self.path.read_text())

    def add(self, url: str, overall_score: float, check_scores: dict[str, float], timestamp: str | None = None) -> None:
        """Record a new snapshot for a site."""
        from datetime import datetime, timezone

        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        entry = {
            "timestamp": timestamp,
            "overall_score": round(overall_score, 3),
            "check_scores": {k: round(v, 3) for k, v in check_scores.items()},
        }

        if url not in self._data:
            self._data[url] = []
        self._data[url].append(entry)
        self._save()

    def add_from_result(self, result: dict) -> None:
        """Record from a standard analysis result dict."""
        url = result["url"]
        overall = result["overall_score"]
        checks = {c["name"]: c["score"] for c in result.get("checks", [])}
        ts = result.get("timestamp")
        self.add(url, overall, checks, timestamp=ts)

    def get_trend(self, url: str) -> SiteTrend:
        """Get the full trend for a site."""
        entries = self._data.get(url, [])
        snapshots = [
            ScoreSnapshot(
                timestamp=e["timestamp"],
                overall_score=e["overall_score"],
                check_scores=e.get("check_scores", {}),
            )
            for e in sorted(entries, key=lambda e: e["timestamp"])
        ]
        return SiteTrend(url=url, snapshots=snapshots)

    def all_urls(self) -> list[str]:
        """Get all tracked URLs."""
        return sorted(self._data.keys())

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))


def render_trend_table(trend: SiteTrend) -> str:
    """Render a trend as a text table."""
    if not trend.snapshots:
        return f"No history for {trend.url}"

    lines = [f"Trend: {trend.url}  ({len(trend.snapshots)} snapshots, {trend.direction})\n"]

    for snap in trend.snapshots:
        dt_str = snap.dt.strftime("%Y-%m-%d %H:%M")
        bar = "█" * int(snap.overall_score * 10) + "░" * (10 - int(snap.overall_score * 10))
        lines.append(f"  {dt_str}  {bar}  {snap.overall_score:.0%}")

    if trend.delta is not None:
        sign = "+" if trend.delta > 0 else ""
        lines.append(f"\n  Change: {sign}{trend.delta:.0%}")

    return "\n".join(lines)
