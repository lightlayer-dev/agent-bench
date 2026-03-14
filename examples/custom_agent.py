#!/usr/bin/env python3
"""Example custom agent for agent-bench.

This demonstrates the JSON-lines protocol for the custom adapter.
It reads a task from stdin, performs some mock actions, and reports results.

Usage:
    AGENT_BENCH_CUSTOM_CMD="python examples/custom_agent.py" \
    agent-bench run tasks/example.yaml --model claude-sonnet --adapter custom

Protocol:
    - Input (stdin, line 1): JSON task payload
    - Output (stdout): JSON-lines with step reports and final result
    - Steps: {"step": N, "action": "...", "result": "...", ...}
    - Final: {"done": true, "success": true/false, "summary": "..."}
    - Optional per-step: "input_tokens", "output_tokens", "cost_usd"
"""

import json
import sys


def main():
    # Read the task from stdin
    task_line = sys.stdin.readline()
    payload = json.loads(task_line)

    task = payload["task"]
    site = payload["site"]
    model = payload.get("model", "unknown")

    print(json.dumps({
        "step": 1,
        "action": "navigate",
        "result": f"Loaded {site}",
    }), flush=True)

    # Process each step from the task definition
    for i, step in enumerate(task.get("steps", []), start=2):
        print(json.dumps({
            "step": i,
            "action": step.get("action", "unknown"),
            "result": f"Executed: {step.get('description', step.get('action'))}",
            "input_tokens": 500,    # Report token usage if known
            "output_tokens": 100,
        }), flush=True)

    # Report final result
    print(json.dumps({
        "done": True,
        "success": True,
        "summary": f"Completed task '{task['name']}' on {site} using {model}",
    }), flush=True)


if __name__ == "__main__":
    main()
