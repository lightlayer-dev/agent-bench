"""Adapter for the browser-use agent framework."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from agent_bench.config import ModelProvider
from agent_bench.runner.adapters.base import BaseAdapter, register_adapter

if TYPE_CHECKING:
    from agent_bench.config import ModelConfig
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


def _get_llm(model_config: ModelConfig):
    """Create an LLM instance for browser-use.

    browser-use 0.12+ has its own LLM wrappers, but also supports
    LangChain chat models. We use browser-use's built-in wrappers
    when available, falling back to langchain.
    """
    api_key_env = model_config.api_key_env
    api_key = os.environ.get(api_key_env or "")

    if model_config.provider == ModelProvider.ANTHROPIC:
        api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                f"API key not found. Set {api_key_env or 'ANTHROPIC_API_KEY'} environment variable."
            )
        try:
            from browser_use import ChatAnthropic
            return ChatAnthropic(
                model=model_config.model_id,
                api_key=api_key,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )
        except ImportError:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=model_config.model_id,
                api_key=api_key,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )

    elif model_config.provider == ModelProvider.OPENAI:
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                f"API key not found. Set {api_key_env or 'OPENAI_API_KEY'} environment variable."
            )
        try:
            from browser_use import ChatOpenAI
            return ChatOpenAI(
                model=model_config.model_id,
                api_key=api_key,
                temperature=model_config.temperature,
            )
        except ImportError:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model=model_config.model_id,
                api_key=api_key,
                temperature=model_config.temperature,
                max_tokens=model_config.max_tokens,
            )

    elif model_config.provider == ModelProvider.GOOGLE:
        api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                f"API key not found. Set {api_key_env or 'GOOGLE_API_KEY'} environment variable."
            )
        try:
            from browser_use import ChatGoogle
            return ChatGoogle(
                model=model_config.model_id,
                api_key=api_key,
                temperature=model_config.temperature,
            )
        except ImportError:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_config.model_id,
                google_api_key=api_key,
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
        pip install 'agent-bench[browser-use]'
        playwright install chromium
    """

    name = "browser-use"

    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task using browser-use."""
        import asyncio
        return asyncio.run(self._run_async(task, metrics))

    async def _run_async(self, task: Task, metrics: RunMetrics) -> bool:
        """Async implementation of task execution."""
        from browser_use import Agent, BrowserSession, BrowserProfile

        llm = _get_llm(self.model_config)
        prompt = self._build_prompt(task)

        browser = BrowserSession(
            browser_profile=BrowserProfile(headless=True),
        )

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
                    action_desc = str(step)[:200]
                    metrics.record_step(action=action_desc, result="")

            # Try to extract token usage from result
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
