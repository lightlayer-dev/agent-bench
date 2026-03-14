#!/usr/bin/env python3
"""Example custom agent for agent-bench.

This script demonstrates the JSON-lines protocol that custom adapters use
to communicate with agent-bench. Your agent reads a task from stdin and
reports progress + results on stdout.

Usage:
    AGENT_BENCH_CUSTOM_CMD="python examples/custom_agent.py" \
    agent-bench run tasks/example.yaml --model claude-sonnet --adapter custom

Protocol:
    Input (stdin, first line):  JSON task object
    Output (stdout):            One JSON object per line

    Step messages:
        {"step": 1, "action": "navigate", "result": "loaded page",
         "input_tokens": 500, "output_tokens": 100}

    Final message (required):
        {"done": true, "success": true, "summary": "Task completed successfully"}

    Token counts are optional but recommended for cost tracking.
"""

from __future__ import annotations

import json
import sys
import time


def main() -> None:
    # Read task from stdin
    task_line = sys.stdin.readline()
    if not task_line.strip():
        print(json.dumps({"done": True, "success": False, "summary": "No task provided"}))
        return

    task = json.loads(task_line)

    site = task.get("site", "unknown")
    description = task.get("description", "No description")
    steps = task.get("steps", [])

    # --- Your agent logic goes here ---
    # This example just simulates steps. Replace with real browser automation,
    # API calls, or whatever your agent does.

    print(
        json.dumps({
            "step": 1,
            "action": "navigate",
            "result": f"Navigated to {site}",
            "input_tokens": 200,
            "output_tokens": 50,
        }),
        flush=True,
    )
    time.sleep(0.5)

    for i, step in enumerate(steps, start=2):
        action = step.get("action", "unknown")
        print(
            json.dumps({
                "step": i,
                "action": action,
                "result": f"Executed {action}",
                "input_tokens": 300,
                "output_tokens": 80,
            }),
            flush=True,
        )
        time.sleep(0.3)

    # Report final result
    print(
        json.dumps({
            "done": True,
            "success": True,
            "summary": f"Completed task: {description}",
        }),
        flush=True,
    )


if __name__ == "__main__":
    main()
