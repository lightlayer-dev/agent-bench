"""Adapter for custom/external agent implementations.

This adapter lets users plug in any agent by providing an executable
that follows a simple JSON-lines protocol over stdin/stdout.

Usage:
    agent-bench run tasks/example.yaml --adapter custom --adapter-cmd "python my_agent.py"

Protocol:
    1. agent-bench sends a task as JSON on the first line of stdin:
       {"task": {...}, "site": "https://...", "model": "claude-sonnet"}

    2. The agent sends action lines as JSON on stdout:
       {"step": 1, "action": "navigate", "url": "https://...", "result": "loaded"}
       {"step": 2, "action": "click", "target": "Add to Cart", "result": "clicked"}
       ...

    3. The agent sends a final result line:
       {"done": true, "success": true, "summary": "Added item to cart"}

    Each step line is recorded as a metric. The process should exit with
    code 0 on success, non-zero on failure.

Example agent script (my_agent.py):
    import json, sys

    task = json.loads(input())
    print(json.dumps({"step": 1, "action": "start", "result": "loaded"}))
    # ... do your thing ...
    print(json.dumps({"done": True, "success": True, "summary": "completed"}))
"""

from __future__ import annotations

import json
import os
import subprocess
from typing import TYPE_CHECKING

from agent_bench.runner.adapters.base import BaseAdapter, register_adapter

if TYPE_CHECKING:
    from agent_bench.config import ModelConfig
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


@register_adapter
class CustomAdapter(BaseAdapter):
    """Adapter for custom agent implementations via subprocess.

    Runs an external script/binary that implements the agent logic.
    Communicates via a JSON-lines protocol on stdin/stdout.

    Set the command via the AGENT_BENCH_CUSTOM_CMD environment variable
    or pass --adapter-cmd on the CLI.
    """

    name = "custom"

    def __init__(self, model_config: ModelConfig, cmd: str | None = None) -> None:
        super().__init__(model_config)
        self.cmd = cmd or os.environ.get("AGENT_BENCH_CUSTOM_CMD", "")

    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task using a custom external agent."""
        if not self.cmd:
            raise ValueError(
                "No custom agent command configured. "
                "Set AGENT_BENCH_CUSTOM_CMD or pass --adapter-cmd."
            )

        # Build the input payload
        payload = {
            "task": {
                "name": task.name,
                "site": task.site,
                "description": task.description,
                "steps": [
                    {
                        "action": s.action,
                        "params": s.params,
                        "description": s.description,
                    }
                    for s in task.steps
                ],
                "success_criteria": [
                    {
                        "type": c.type,
                        "value": c.value,
                        "description": c.description,
                    }
                    for c in task.success_criteria
                ],
            },
            "site": task.site,
            "model": self.model_config.name,
            "model_id": self.model_config.model_id,
            "provider": self.model_config.provider.value,
        }

        try:
            proc = subprocess.Popen(
                self.cmd,
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send task as first line
            assert proc.stdin is not None
            proc.stdin.write(json.dumps(payload) + "\n")
            proc.stdin.flush()
            proc.stdin.close()

            # Read step-by-step output
            assert proc.stdout is not None
            success = False
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                if data.get("done"):
                    success = data.get("success", False)
                    break

                # Record as a step
                metrics.record_step(
                    action=str(data.get("action", "unknown")),
                    result=str(data.get("result", "")),
                    **{
                        k: v
                        for k, v in data.items()
                        if k not in ("action", "result", "step")
                    },
                )

                # Track tokens if reported
                if "input_tokens" in data:
                    metrics.input_tokens += data["input_tokens"]
                if "output_tokens" in data:
                    metrics.output_tokens += data["output_tokens"]
                if "cost_usd" in data:
                    metrics.estimated_cost_usd += data["cost_usd"]

            proc.wait(timeout=30)

            if proc.returncode != 0:
                stderr = proc.stderr.read() if proc.stderr else ""
                metrics.error = (
                    f"Process exited with code {proc.returncode}: {stderr[:500]}"
                )
                return False

            return success

        except subprocess.TimeoutExpired:
            proc.kill()
            metrics.error = "Custom agent timed out"
            return False
        except Exception as e:
            metrics.error = str(e)
            return False
