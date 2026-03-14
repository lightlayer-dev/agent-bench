"""Adapter for custom/external agent implementations."""

from __future__ import annotations

import subprocess
from typing import TYPE_CHECKING

from agent_bench.runner.adapters.base import BaseAdapter, register_adapter

if TYPE_CHECKING:
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


@register_adapter
class CustomAdapter(BaseAdapter):
    """Adapter for custom agent implementations.

    Runs an external script/binary that implements the agent logic.
    Communicates via stdin/stdout JSON protocol.

    The external agent receives the task as JSON on stdin and should
    output step-by-step actions and a final result as JSON lines on stdout.
    """

    name = "custom"

    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task using a custom external agent."""
        # TODO: Define the JSON protocol for custom agents
        # TODO: Launch external process with task as input
        # TODO: Parse stdout for step recordings
        # TODO: Collect final success/failure result
        raise NotImplementedError("Custom adapter not yet implemented")
