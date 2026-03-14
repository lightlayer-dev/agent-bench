"""Run executor — orchestrates agent benchmark runs."""

from __future__ import annotations

from pathlib import Path

from agent_bench.runner.adapters.base import BaseAdapter, get_adapter
from agent_bench.runner.metrics import AggregateMetrics, RunMetrics
from agent_bench.runner.task import Task
from agent_bench.models.registry import ModelRegistry


class RunResult:
    """Result of a complete benchmark execution."""

    def __init__(self, aggregates: list[AggregateMetrics]) -> None:
        self.aggregates = aggregates

    def summary(self) -> str:
        """Human-readable summary of results."""
        lines = ["Benchmark Results", "=" * 60]
        for agg in self.aggregates:
            lines.append(
                f"\n{agg.task_name} | {agg.model_name} | {agg.adapter_name}"
            )
            lines.append(f"  Success rate: {agg.success_rate:.0%}")
            lines.append(f"  Avg steps:    {agg.avg_steps:.1f}")
            lines.append(f"  Avg time:     {agg.avg_time:.1f}s")
            lines.append(f"  Avg cost:     ${agg.avg_cost:.4f}")
        return "\n".join(lines)


class BenchExecutor:
    """Orchestrates benchmark runs across tasks, models, and adapters."""

    def __init__(
        self,
        task_file: Path,
        model_name: str,
        adapter_name: str,
        num_runs: int = 3,
        output_dir: Path = Path("results"),
    ) -> None:
        self.tasks = Task.from_yaml_multi(task_file) if task_file.suffix in (".yaml", ".yml") else [Task.from_yaml(task_file)]
        self.model_config = ModelRegistry.get(model_name)
        self.adapter_name = adapter_name
        self.num_runs = num_runs
        self.output_dir = output_dir

    def execute(self) -> RunResult:
        """Run all tasks and collect metrics."""
        aggregates: list[AggregateMetrics] = []

        for task in self.tasks:
            agg = AggregateMetrics(
                task_name=task.name,
                model_name=self.model_config.name,
                adapter_name=self.adapter_name,
            )

            adapter = get_adapter(self.adapter_name, self.model_config)

            for i in range(self.num_runs):
                metrics = RunMetrics(
                    task_name=task.name,
                    model_name=self.model_config.name,
                    adapter_name=self.adapter_name,
                    run_index=i,
                )
                metrics.start()

                try:
                    result = adapter.run_task(task, metrics)
                    metrics.success = result
                except Exception as e:
                    metrics.error = str(e)
                    metrics.success = False
                finally:
                    metrics.stop()

                agg.runs.append(metrics)

            aggregates.append(agg)

        self._save_results(aggregates)
        return RunResult(aggregates)

    def _save_results(self, aggregates: list[AggregateMetrics]) -> None:
        """Save results to disk."""
        from agent_bench.results.store import ResultStore

        self.output_dir.mkdir(parents=True, exist_ok=True)
        store = ResultStore(self.output_dir)
        store.save(aggregates)
