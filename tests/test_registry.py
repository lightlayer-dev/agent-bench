"""Tests for model registry."""

import pytest
from agent_bench.models.registry import ModelRegistry, _custom_models
from agent_bench.config import ModelConfig, ModelProvider


class TestModelRegistry:
    def setup_method(self):
        _custom_models.clear()

    def test_get_builtin_model(self):
        config = ModelRegistry.get("claude-sonnet")
        assert config.name == "claude-sonnet"
        assert config.provider == ModelProvider.ANTHROPIC

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            ModelRegistry.get("nonexistent-model")

    def test_register_custom(self):
        custom = ModelConfig(
            name="my-model",
            provider=ModelProvider.CUSTOM,
            model_id="custom-v1",
        )
        ModelRegistry.register(custom)
        assert ModelRegistry.get("my-model") is custom

    def test_custom_overrides_builtin(self):
        custom = ModelConfig(
            name="claude-sonnet",
            provider=ModelProvider.ANTHROPIC,
            model_id="claude-sonnet-custom",
        )
        ModelRegistry.register(custom)
        assert ModelRegistry.get("claude-sonnet").model_id == "claude-sonnet-custom"

    def test_list_models(self):
        models = ModelRegistry.list_models()
        assert "claude-sonnet" in models
        assert "gpt-4o" in models
        assert isinstance(models, list)
        assert models == sorted(models)

    def test_all_builtins_have_api_key_env(self):
        for name in ModelRegistry.list_models():
            config = ModelRegistry.get(name)
            assert config.api_key_env is not None
