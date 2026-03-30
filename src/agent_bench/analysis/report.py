"""Analysis report generation."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_bench.analysis.models import CheckResult


@dataclass
class AnalysisReport:
    """Complete analysis report for a site."""

    url: str
    overall_score: float
    check_results: list[CheckResult] = field(default_factory=list)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def render(self, fmt: str = "table") -> str:
        """Render the report in the specified format."""
        if fmt == "json":
            return self.to_json()
        elif fmt == "markdown":
            return self._render_markdown()
        elif fmt == "html":
            from agent_bench.analysis.html_report import render_html_report

            return render_html_report(self)
        else:
            return self._render_table()

    def to_json(self) -> str:
        """Serialize report to JSON."""
        from agent_bench.analysis.schema import SCHEMA_VERSION

        return json.dumps(
            {
                "url": self.url,
                "timestamp": self.timestamp,
                "schema_version": SCHEMA_VERSION,
                "overall_score": round(self.overall_score, 3),
                "checks": [
                    {
                        "name": r.name,
                        "score": round(r.score, 3),
                        "findings": r.findings,
                        "details": r.details,
                    }
                    for r in self.check_results
                ],
            },
            indent=2,
        )

    def _render_table(self) -> str:
        """Render as a rich-compatible table string."""
        lines = [f"Agent-Readiness Score: {self.overall_score:.0%}\n"]
        for r in self.check_results:
            bar = "█" * int(r.score * 10) + "░" * (10 - int(r.score * 10))
            lines.append(f"  {r.name:<12} {bar} {r.score:.0%}")
            for finding in r.findings:
                lines.append(f"               → {finding}")
        return "\n".join(lines)

    def _render_markdown(self) -> str:
        """Render as markdown."""
        lines = [f"# Agent-Readiness Report: {self.url}\n"]
        lines.append(f"**Overall Score: {self.overall_score:.0%}**\n")
        for r in self.check_results:
            lines.append(f"## {r.name.title()} — {r.score:.0%}")
            for finding in r.findings:
                lines.append(f"- {finding}")
            lines.append("")
        return "\n".join(lines)
