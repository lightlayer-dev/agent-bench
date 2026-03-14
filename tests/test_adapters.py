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
                SuccessCriterion(type="text_contains", value="price", description="Should see prices"),
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


class TestPlaywrightAdapter:
    def test_build_task_prompt(self):
        from agent_bench.runner.adapters.playwright_agent import PlaywrightAdapter

        adapter = PlaywrightAdapter(_model_config())
        task = Task(
            name="test",
            site="https://example.com",
            description="Search for headphones",
            steps=[
                TaskStep(action="search", params={"query": "headphones"}, description="Use search bar"),
            ],
        )
        prompt = adapter._build_task_prompt(task)
        assert "Search for headphones" in prompt
        assert "https://example.com" in prompt
        assert "Use search bar" in prompt

    def test_format_a11y_node(self):
        from agent_bench.runner.adapters.playwright_agent import PlaywrightAdapter

        adapter = PlaywrightAdapter(_model_config())
        node = {
            "role": "button",
            "name": "Submit",
            "children": [
                {"role": "text", "name": "Submit Form"},
            ],
        }
        formatted = adapter._format_a11y_node(node, depth=0, max_depth=3)
        assert "button" in formatted
        assert "Submit" in formatted
        assert "text" in formatted

    def test_format_a11y_max_depth(self):
        from agent_bench.runner.adapters.playwright_agent import PlaywrightAdapter

        adapter = PlaywrightAdapter(_model_config())
        node = {"role": "deep", "name": "too deep"}
        result = adapter._format_a11y_node(node, depth=5, max_depth=4)
        assert result == ""
