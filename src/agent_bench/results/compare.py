"""Compare results across benchmark runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# --- Live run comparison ---


@dataclass
class ComparisonRow:
    """A single row in a comparison table."""

    task: str
    model: str
    adapter: str
    success_rate: float
    avg_steps: float
    avg_time: float
    avg_cost: float


@dataclass
class Comparison:
    """Comparison across multiple benchmark runs."""

    rows: list[ComparisonRow] = field(default_factory=list)

    def render(self, fmt: str = "table") -> str:
        """Render comparison in the specified format."""
        if fmt == "json":
            return json.dumps([vars(r) for r in self.rows], indent=2)
        elif fmt == "markdown":
            return self._render_markdown()
        else:
            return self._render_table()

    def _render_table(self) -> str:
        lines = [
            f"{'Task':<25} {'Model':<18} {'Adapter':<14} {'Success':>8} {'Steps':>7} {'Time':>8} {'Cost':>10}",
            "-" * 92,
        ]
        for r in self.rows:
            lines.append(
                f"{r.task:<25} {r.model:<18} {r.adapter:<14} {r.success_rate:>7.0%} {r.avg_steps:>7.1f} {r.avg_time:>7.1f}s ${r.avg_cost:>8.4f}"
            )
        return "\n".join(lines)

    def _render_markdown(self) -> str:
        lines = [
            "| Task | Model | Adapter | Success | Steps | Time | Cost |",
            "|------|-------|---------|---------|-------|------|------|",
        ]
        for r in self.rows:
            lines.append(
                f"| {r.task} | {r.model} | {r.adapter} | {r.success_rate:.0%} | {r.avg_steps:.1f} | {r.avg_time:.1f}s | ${r.avg_cost:.4f} |"
            )
        return "\n".join(lines)


def compare_runs(result_files: list[Path]) -> Comparison:
    """Load and compare multiple result files."""
    rows: list[ComparisonRow] = []

    for filepath in result_files:
        data = json.loads(filepath.read_text())
        for result in data.get("results", []):
            rows.append(
                ComparisonRow(
                    task=result["task"],
                    model=result["model"],
                    adapter=result["adapter"],
                    success_rate=result["success_rate"],
                    avg_steps=result["avg_steps"],
                    avg_time=result["avg_time"],
                    avg_cost=result["avg_cost"],
                )
            )

    # Sort by task, then success rate (descending)
    rows.sort(key=lambda r: (r.task, -r.success_rate))
    return Comparison(rows=rows)


# --- Static analysis comparison ---


@dataclass
class ScoreDelta:
    """Score change for a single check between two analysis snapshots."""

    check: str
    before: float
    after: float

    @property
    def delta(self) -> float:
        return self.after - self.before

    @property
    def direction(self) -> str:
        if self.delta > 0.005:
            return "▲"
        elif self.delta < -0.005:
            return "▼"
        return "="


@dataclass
class AnalysisComparison:
    """Comparison between two static analysis snapshots of the same site."""

    url: str
    before_score: float
    after_score: float
    deltas: list[ScoreDelta] = field(default_factory=list)
    before_file: str = ""
    after_file: str = ""

    @property
    def overall_delta(self) -> float:
        return self.after_score - self.before_score

    @property
    def overall_direction(self) -> str:
        d = self.overall_delta
        if d > 0.005:
            return "▲"
        elif d < -0.005:
            return "▼"
        return "="

    def render(self, fmt: str = "table") -> str:
        if fmt == "json":
            return json.dumps(self._to_dict(), indent=2)
        elif fmt == "markdown":
            return self._render_markdown()
        else:
            return self._render_table()

    def _to_dict(self) -> dict:
        return {
            "url": self.url,
            "before_score": self.before_score,
            "after_score": self.after_score,
            "overall_delta": self.overall_delta,
            "before_file": self.before_file,
            "after_file": self.after_file,
            "checks": [
                {
                    "check": d.check,
                    "before": d.before,
                    "after": d.after,
                    "delta": d.delta,
                    "direction": d.direction,
                }
                for d in self.deltas
            ],
        }

    def _render_table(self) -> str:
        lines = [
            f"Score Comparison: {self.url}",
            "",
            f"  Overall: {self.before_score:.0%} → {self.after_score:.0%}  {self.overall_direction} {self.overall_delta:+.1%}",
            "",
            f"  {'Check':<14} {'Before':>8} {'After':>8} {'Delta':>8}",
            f"  {'-' * 42}",
        ]
        for d in self.deltas:
            lines.append(
                f"  {d.check:<14} {d.before:>7.0%} {d.after:>7.0%}  {d.direction} {d.delta:+.1%}"
            )
        return "\n".join(lines)

    def _render_markdown(self) -> str:
        lines = [
            f"## Score Comparison: {self.url}",
            "",
            f"**Overall:** {self.before_score:.0%} → {self.after_score:.0%} ({self.overall_direction} {self.overall_delta:+.1%})",
            "",
            "| Check | Before | After | Delta |",
            "|-------|--------|-------|-------|",
        ]
        for d in self.deltas:
            lines.append(
                f"| {d.check} | {d.before:.0%} | {d.after:.0%} | {d.direction} {d.delta:+.1%} |"
            )
        return "\n".join(lines)


def compare_analyses(before_file: Path, after_file: Path) -> AnalysisComparison:
    """Compare two static analysis result files for the same site.

    Each file should be a JSON object with 'url', 'overall_score', and 'checks'
    (list of dicts with 'name' and 'score').
    """
    before = json.loads(before_file.read_text())
    after = json.loads(after_file.read_text())

    url = after.get("url", before.get("url", "unknown"))

    before_checks = {c["name"]: c["score"] for c in before.get("checks", [])}
    after_checks = {c["name"]: c["score"] for c in after.get("checks", [])}

    all_checks = sorted(set(before_checks) | set(after_checks))
    deltas = [
        ScoreDelta(
            check=name,
            before=before_checks.get(name, 0.0),
            after=after_checks.get(name, 0.0),
        )
        for name in all_checks
    ]

    return AnalysisComparison(
        url=url,
        before_score=before.get("overall_score", 0.0),
        after_score=after.get("overall_score", 0.0),
        deltas=deltas,
        before_file=str(before_file),
        after_file=str(after_file),
    )
