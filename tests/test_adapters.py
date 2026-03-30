"""Tests for agent adapter scaffolding (no LLM calls)."""

from agent_bench.runner.adapters.base import _ADAPTERS, get_adapter
from agent_bench.runner.task import Task, TaskStep, SuccessCriterion
from agent_bench.config import ModelConfig, ModelProvider


def _model_config() -> ModelConfig:
    return ModelConfig(
        name="test-model",
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
    )


class TestAdapterRegistry:
    def test_browser_use_registered(self):
        assert "browser-use" in _ADAPTERS

    def test_playwright_registered(self):
        assert "playwright" in _ADAPTERS

    def test_custom_registered(self):
        assert "custom" in _ADAPTERS

    def test_get_adapter(self):
        adapter = get_adapter("browser-use", _model_config())
        assert adapter.name == "browser-use"

    def test_get_unknown_adapter(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexistent", _model_config())


class TestBrowserUseAdapter:
    def test_build_prompt_basic(self):
        from agent_bench.runner.adapters.browser_use import BrowserUseAdapter

        adapter = BrowserUseAdapter(_model_config())
        task = Task(
            name="test",
            site="https://example.com",
            description="Find the pricing page",
            steps=[
                TaskStep(action="navigate", params={"url": "https://example.com"}),
                TaskStep(action="find_pricing", description="Navigate to pricing"),
            ],
            success_criteria=[
                SuccessCriterion(
                    type="text_contains", value="price", description="Should see prices"
                ),
            ],
        )
        prompt = adapter._build_prompt(task)
        assert "Find the pricing page" in prompt
        assert "Navigate to pricing" in prompt
        assert "Should see prices" in prompt

    def test_build_prompt_no_steps(self):
        from agent_bench.runner.adapters.browser_use import BrowserUseAdapter

        adapter = BrowserUseAdapter(_model_config())
        task = Task(name="test", site="https://example.com", description="Just browse")
        prompt = adapter._build_prompt(task)
        assert "Just browse" in prompt


class TestCustomAdapter:
    def test_no_cmd_raises(self):
        import pytest
        from agent_bench.runner.adapters.custom import CustomAdapter
        from agent_bench.runner.metrics import RunMetrics

        adapter = CustomAdapter(_model_config(), cmd="")
        task = Task(name="test", site="https://example.com", description="test")
        metrics = RunMetrics(
            task_name="test", model_name="test", adapter_name="custom", run_index=0
        )

        with pytest.raises(ValueError, match="No custom agent command"):
            adapter.run_task(task, metrics)

    def test_successful_run(self):
        from agent_bench.runner.adapters.custom import CustomAdapter
        from agent_bench.runner.metrics import RunMetrics

        # A simple agent that reads stdin and reports success
        cmd = '''python3 -c "
import json, sys
task = json.loads(sys.stdin.readline())
print(json.dumps({'step': 1, 'action': 'test', 'result': 'ok', 'input_tokens': 10}))
print(json.dumps({'done': True, 'success': True, 'summary': 'done'}))
"'''
        adapter = CustomAdapter(_model_config(), cmd=cmd)
        task = Task(name="test", site="https://example.com", description="test task")
        metrics = RunMetrics(
            task_name="test", model_name="test", adapter_name="custom", run_index=0
        )

        result = adapter.run_task(task, metrics)
        assert result is True
        assert metrics.steps_taken == 1
        assert metrics.input_tokens == 10

    def test_failed_run(self):
        from agent_bench.runner.adapters.custom import CustomAdapter
        from agent_bench.runner.metrics import RunMetrics

        cmd = '''python3 -c "
import json, sys
task = json.loads(sys.stdin.readline())
print(json.dumps({'done': True, 'success': False, 'summary': 'failed'}))
"'''
        adapter = CustomAdapter(_model_config(), cmd=cmd)
        task = Task(name="test", site="https://example.com", description="test")
        metrics = RunMetrics(
            task_name="test", model_name="test", adapter_name="custom", run_index=0
        )

        result = adapter.run_task(task, metrics)
        assert result is False

    def test_process_crash(self):
        from agent_bench.runner.adapters.custom import CustomAdapter
        from agent_bench.runner.metrics import RunMetrics

        cmd = "python3 -c 'import sys; sys.exit(1)'"
        adapter = CustomAdapter(_model_config(), cmd=cmd)
        task = Task(name="test", site="https://example.com", description="test")
        metrics = RunMetrics(
            task_name="test", model_name="test", adapter_name="custom", run_index=0
        )

        result = adapter.run_task(task, metrics)
        assert result is False
        assert metrics.error is not None


class TestPlaywrightAdapter:
    def test_build_task_prompt(self):
        from agent_bench.runner.adapters.playwright_agent import PlaywrightAdapter

        adapter = PlaywrightAdapter(_model_config())
        task = Task(
            name="test",
            site="https://example.com",
            description="Search for headphones",
            steps=[
                TaskStep(
                    action="search",
                    params={"query": "headphones"},
                    description="Use search bar",
                ),
            ],
        )
        prompt = adapter._build_task_prompt(task)
        assert "Search for headphones" in prompt
        assert "https://example.com" in prompt
        assert "Use search bar" in prompt

    def test_build_task_prompt_no_steps(self):
        from agent_bench.runner.adapters.playwright_agent import PlaywrightAdapter

        adapter = PlaywrightAdapter(_model_config())
        task = Task(name="test", site="https://example.com", description="Just browse")
        prompt = adapter._build_task_prompt(task)
        assert "Just browse" in prompt
        assert "https://example.com" in prompt
