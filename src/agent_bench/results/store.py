"""Results storage — save and load benchmark results."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_bench.runner.metrics import AggregateMetrics


class ResultStore:
    """Save and load benchmark results as JSON files."""

    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def save(self, aggregates: list[AggregateMetrics]) -> Path:
        """Save aggregate results to a timestamped JSON file."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"bench_{timestamp}.json"
        filepath = self.output_dir / filename

        data = {
            "timestamp": timestamp,
            "results": [
                {
                    "task": agg.task_name,
                    "model": agg.model_name,
                    "adapter": agg.adapter_name,
                    "success_rate": agg.success_rate,
                    "avg_steps": agg.avg_steps,
                    "avg_time": agg.avg_time,
                    "avg_cost": agg.avg_cost,
                    "runs": [r.to_dict() for r in agg.runs],
                }
                for agg in aggregates
            ],
        }

        filepath.write_text(json.dumps(data, indent=2))
        return filepath

    def load(self, filepath: Path) -> dict:
        """Load results from a JSON file."""
        return json.loads(filepath.read_text())

    def list_results(self) -> list[Path]:
        """List all result files in the output directory."""
        return sorted(self.output_dir.glob("bench_*.json"), reverse=True)
