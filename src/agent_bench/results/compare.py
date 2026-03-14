"""Compare results across benchmark runs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


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
