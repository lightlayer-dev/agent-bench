"""Metrics collection for agent benchmark runs."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RunMetrics:
    """Metrics collected during a single agent run."""

    task_name: str
    model_name: str
    adapter_name: str
    run_index: int

    success: bool = False
    steps_taken: int = 0
    wall_time_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    error: str | None = None
    trace: list[dict[str, object]] = field(default_factory=list)

    # Timing
    _start_time: float = field(default=0.0, repr=False)

    def start(self) -> None:
        """Mark the start of a run."""
        self._start_time = time.monotonic()

    def stop(self) -> None:
        """Mark the end of a run."""
        self.wall_time_seconds = time.monotonic() - self._start_time

    def record_step(self, action: str, result: str, **kwargs: object) -> None:
        """Record an agent action step."""
        self.steps_taken += 1
        self.trace.append({"step": self.steps_taken, "action": action, "result": result, **kwargs})

    def to_dict(self) -> dict[str, object]:
        """Serialize to a dictionary."""
        return {
            "task_name": self.task_name,
            "model_name": self.model_name,
            "adapter_name": self.adapter_name,
            "run_index": self.run_index,
            "success": self.success,
            "steps_taken": self.steps_taken,
            "wall_time_seconds": round(self.wall_time_seconds, 2),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "error": self.error,
            "trace": self.trace,
        }


@dataclass
class AggregateMetrics:
    """Aggregated metrics across multiple runs of the same task × model × adapter."""

    task_name: str
    model_name: str
    adapter_name: str
    runs: list[RunMetrics] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if not self.runs:
            return 0.0
        return sum(1 for r in self.runs if r.success) / len(self.runs)

    @property
    def avg_steps(self) -> float:
        successful = [r for r in self.runs if r.success]
        if not successful:
            return 0.0
        return sum(r.steps_taken for r in successful) / len(successful)

    @property
    def avg_time(self) -> float:
        successful = [r for r in self.runs if r.success]
        if not successful:
            return 0.0
        return sum(r.wall_time_seconds for r in successful) / len(successful)

    @property
    def avg_cost(self) -> float:
        return sum(r.estimated_cost_usd for r in self.runs) / len(self.runs) if self.runs else 0.0
