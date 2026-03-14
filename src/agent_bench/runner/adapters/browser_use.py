"""Adapter for the browser-use agent framework."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_bench.runner.adapters.base import BaseAdapter, register_adapter

if TYPE_CHECKING:
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


@register_adapter
class BrowserUseAdapter(BaseAdapter):
    """Adapter for browser-use (https://github.com/browser-use/browser-use).

    browser-use provides a high-level agent that can navigate websites
    using natural language instructions with vision models.
    """

    name = "browser-use"

    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task using browser-use."""
        # TODO: Import and configure browser-use Agent
        # TODO: Pass task description as the agent's goal
        # TODO: Hook into browser-use callbacks to record steps
        # TODO: Evaluate success criteria after agent completes
        raise NotImplementedError("browser-use adapter not yet implemented")
