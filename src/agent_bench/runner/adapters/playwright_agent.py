"""Adapter for a custom Playwright-based agent with LLM decision-making."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from agent_bench.config import ModelProvider
from agent_bench.runner.adapters.base import BaseAdapter, register_adapter

if TYPE_CHECKING:
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


SYSTEM_PROMPT = """You are a web automation agent. You interact with web pages by choosing actions.

You will receive the page's accessibility tree (a structured view of the page content).
Respond with a JSON action to take.

Available actions:
- {"action": "click", "ref": "<element_ref>"}
- {"action": "type", "ref": "<element_ref>", "text": "<text>"}
- {"action": "navigate", "url": "<url>"}
- {"action": "scroll", "direction": "up|down"}
- {"action": "wait", "seconds": <n>}
- {"action": "done", "success": true|false, "summary": "<what happened>"}

Rules:
- Always respond with valid JSON
- Use element refs from the accessibility tree
- When the task is complete, use the "done" action
- If stuck after 3 attempts, use "done" with success=false
"""


@register_adapter
class PlaywrightAdapter(BaseAdapter):
    """Adapter for a custom Playwright-based agent.

    Uses Playwright for browser automation with an LLM deciding
    which actions to take based on the page's accessibility tree.

    This is a lower-level alternative to browser-use that gives more
    control over the agent loop.

    Requires:
        pip install playwright
        playwright install chromium
    """

    name = "playwright"

    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task using Playwright + LLM."""
        import asyncio
        return asyncio.run(self._run_async(task, metrics))

    async def _run_async(self, task: Task, metrics: RunMetrics) -> bool:
        """Async implementation of the agent loop."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                # Navigate to the task site
                await page.goto(task.site, wait_until="domcontentloaded", timeout=30000)

                prompt = self._build_task_prompt(task)
                messages = [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ]

                max_steps = 30
                for step in range(max_steps):
                    # Capture page state
                    a11y_tree = await self._get_accessibility_tree(page)
                    current_url = page.url

                    state_msg = (
                        f"Current URL: {current_url}\n"
                        f"Page state:\n{a11y_tree}\n\n"
                        f"What action should I take next?"
                    )
                    messages.append({"role": "user", "content": state_msg})

                    # Ask LLM for next action
                    response = await self._call_llm(messages)
                    messages.append({"role": "assistant", "content": response})

                    # Parse and execute action
                    try:
                        action = json.loads(response)
                    except json.JSONDecodeError:
                        # Try to extract JSON from the response
                        import re
                        match = re.search(r'\{[^}]+\}', response)
                        if match:
                            action = json.loads(match.group())
                        else:
                            metrics.record_step(action="parse_error", result=response[:200])
                            continue

                    action_type = action.get("action", "unknown")
                    metrics.record_step(action=action_type, result=json.dumps(action)[:200])

                    if action_type == "done":
                        return action.get("success", False)
                    elif action_type == "click":
                        ref = action.get("ref", "")
                        try:
                            await page.locator(f"[data-ref='{ref}']").first.click(timeout=5000)
                        except Exception:
                            try:
                                await page.click(f"text={ref}", timeout=5000)
                            except Exception as e:
                                messages.append({"role": "user", "content": f"Click failed: {e}"})
                    elif action_type == "type":
                        ref = action.get("ref", "")
                        text = action.get("text", "")
                        try:
                            await page.locator(f"[data-ref='{ref}']").first.fill(text, timeout=5000)
                        except Exception:
                            try:
                                await page.fill(f"[name='{ref}']", text, timeout=5000)
                            except Exception as e:
                                messages.append({"role": "user", "content": f"Type failed: {e}"})
                    elif action_type == "navigate":
                        url = action.get("url", "")
                        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    elif action_type == "scroll":
                        direction = action.get("direction", "down")
                        delta = -500 if direction == "up" else 500
                        await page.mouse.wheel(0, delta)
                        await page.wait_for_timeout(500)
                    elif action_type == "wait":
                        seconds = min(action.get("seconds", 1), 5)
                        await page.wait_for_timeout(int(seconds * 1000))

                # Ran out of steps
                return False

            except Exception as e:
                metrics.error = str(e)
                return False
            finally:
                await browser.close()

    async def _get_accessibility_tree(self, page) -> str:
        """Get the accessibility tree of the page using Playwright's aria snapshot."""
        try:
            snapshot = await page.locator("body").aria_snapshot()
            if snapshot:
                # Truncate to avoid blowing up context
                return snapshot[:4000]
            return "(empty page)"
        except Exception:
            # Fallback: get page title and visible text
            try:
                title = await page.title()
                text = await page.inner_text("body")
                return f"Title: {title}\n\nContent:\n{text[:2000]}"
            except Exception:
                return "(could not read page)"

    async def _call_llm(self, messages: list[dict]) -> str:
        """Call the LLM with the message history."""
        if self.model_config.provider == ModelProvider.ANTHROPIC:
            import httpx

            api_key = os.environ.get(self.model_config.api_key_env or "ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError(
                    f"API key not found. Set {self.model_config.api_key_env or 'ANTHROPIC_API_KEY'} environment variable."
                )
            system = messages[0]["content"] if messages[0]["role"] == "system" else ""
            chat_messages = [m for m in messages if m["role"] != "system"]

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model_config.model_id,
                        "max_tokens": self.model_config.max_tokens,
                        "temperature": self.model_config.temperature,
                        "system": system,
                        "messages": chat_messages,
                    },
                    timeout=60,
                )
                data = resp.json()
                return data["content"][0]["text"]

        elif self.model_config.provider == ModelProvider.OPENAI:
            import httpx

            api_key = os.environ.get(self.model_config.api_key_env or "OPENAI_API_KEY")
            if not api_key:
                raise ValueError(
                    f"API key not found. Set {self.model_config.api_key_env or 'OPENAI_API_KEY'} environment variable."
                )

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model_config.model_id,
                        "messages": messages,
                        "temperature": self.model_config.temperature,
                        "max_tokens": self.model_config.max_tokens,
                    },
                    timeout=60,
                )
                data = resp.json()
                return data["choices"][0]["message"]["content"]

        else:
            raise ValueError(f"Unsupported provider: {self.model_config.provider}")

    def _build_task_prompt(self, task: Task) -> str:
        """Build the initial task prompt."""
        parts = [f"Task: {task.description}", f"Site: {task.site}"]

        if task.steps:
            parts.append("\nExpected steps:")
            for i, step in enumerate(task.steps, 1):
                desc = step.description or step.action
                parts.append(f"  {i}. {desc}")

        if task.success_criteria:
            parts.append("\nSuccess criteria:")
            for c in task.success_criteria:
                parts.append(f"  - {c.description or c.value}")

        parts.append("\nBegin by examining the page state below.")
        return "\n".join(parts)
