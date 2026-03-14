"""Adapter for the browser-use agent framework."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from agent_bench.config import ModelProvider
from agent_bench.runner.adapters.base import BaseAdapter, register_adapter

if TYPE_CHECKING:
    from agent_bench.config import ModelConfig
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


def _get_llm(model_config: ModelConfig):
    """Create a LangChain LLM instance from model config."""
    if model_config.provider == ModelProvider.ANTHROPIC:
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            model=model_config.model_id,
            api_key=os.environ.get(model_config.api_key_env or "ANTHROPIC_API_KEY"),
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )
    elif model_config.provider == ModelProvider.OPENAI:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_config.model_id,
            api_key=os.environ.get(model_config.api_key_env or "OPENAI_API_KEY"),
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )
    elif model_config.provider == ModelProvider.GOOGLE:
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=model_config.model_id,
            google_api_key=os.environ.get(model_config.api_key_env or "GOOGLE_API_KEY"),
            temperature=model_config.temperature,
            max_output_tokens=model_config.max_tokens,
        )
    else:
        raise ValueError(f"Unsupported provider for browser-use: {model_config.provider}")


@register_adapter
class BrowserUseAdapter(BaseAdapter):
    """Adapter for browser-use (https://github.com/browser-use/browser-use).

    browser-use provides a high-level agent that can navigate websites
    using natural language instructions with vision models.

    Requires:
        pip install browser-use langchain-anthropic  (or langchain-openai, etc.)
        playwright install chromium
    """

    name = "browser-use"

    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task using browser-use."""
        import asyncio
        return asyncio.run(self._run_async(task, metrics))

    async def _run_async(self, task: Task, metrics: RunMetrics) -> bool:
        """Async implementation of task execution."""
        from browser_use import Agent, Browser, BrowserConfig

        llm = _get_llm(self.model_config)

        # Build the task prompt from the task definition
        prompt = self._build_prompt(task)

        browser = Browser(config=BrowserConfig(
            headless=True,
        ))

        agent = Agent(
            task=prompt,
            llm=llm,
            browser=browser,
            max_actions_per_step=3,
        )

        try:
            result = await agent.run(max_steps=50)

            # Extract metrics from the agent's history
            if hasattr(result, 'history') and result.history:
                for i, step in enumerate(result.history):
                    action_desc = str(step.get('action', 'unknown')) if isinstance(step, dict) else str(step)
                    result_desc = str(step.get('result', '')) if isinstance(step, dict) else ''
                    metrics.record_step(
                        action=action_desc[:200],
                        result=result_desc[:200],
                    )

            # Try to extract token usage
            if hasattr(result, 'total_input_tokens'):
                metrics.input_tokens = result.total_input_tokens or 0
            if hasattr(result, 'total_output_tokens'):
                metrics.output_tokens = result.total_output_tokens or 0

            # Determine success
            is_done = bool(result.is_done()) if hasattr(result, 'is_done') else True
            return is_done

        except Exception as e:
            metrics.error = str(e)
            return False
        finally:
            await browser.close()

    def _build_prompt(self, task: Task) -> str:
        """Build a natural language prompt from a task definition."""
        parts = [task.description]

        if task.steps:
            parts.append("\nSteps:")
            for i, step in enumerate(task.steps, 1):
                desc = step.description or step.action
                parts.append(f"  {i}. {desc}")
                if step.params:
                    for k, v in step.params.items():
                        parts.append(f"     {k}: {v}")

        if task.success_criteria:
            parts.append("\nSuccess criteria:")
            for criterion in task.success_criteria:
                desc = criterion.description or criterion.value
                parts.append(f"  - {desc}")

        return "\n".join(parts)
