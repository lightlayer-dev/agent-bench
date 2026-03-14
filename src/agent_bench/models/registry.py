"""Model registry — pre-configured foundation model definitions."""

from __future__ import annotations

from agent_bench.config import ModelConfig, ModelProvider


# Pre-configured models
_BUILTIN_MODELS: dict[str, ModelConfig] = {
    "claude-sonnet": ModelConfig(
        name="claude-sonnet",
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-sonnet-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "claude-opus": ModelConfig(
        name="claude-opus",
        provider=ModelProvider.ANTHROPIC,
        model_id="claude-opus-4-20250514",
        api_key_env="ANTHROPIC_API_KEY",
    ),
    "gpt-4o": ModelConfig(
        name="gpt-4o",
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o",
        api_key_env="OPENAI_API_KEY",
    ),
    "gpt-4o-mini": ModelConfig(
        name="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        model_id="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
    ),
    "gemini-pro": ModelConfig(
        name="gemini-pro",
        provider=ModelProvider.GOOGLE,
        model_id="gemini-2.5-pro",
        api_key_env="GOOGLE_API_KEY",
    ),
}

_custom_models: dict[str, ModelConfig] = {}


class ModelRegistry:
    """Registry for foundation model configurations."""

    @staticmethod
    def get(name: str) -> ModelConfig:
        """Get a model config by name."""
        if name in _custom_models:
            return _custom_models[name]
        if name in _BUILTIN_MODELS:
            return _BUILTIN_MODELS[name]
        available = ", ".join(sorted({*_BUILTIN_MODELS, *_custom_models}))
        raise ValueError(f"Unknown model '{name}'. Available: {available}")

    @staticmethod
    def register(config: ModelConfig) -> None:
        """Register a custom model configuration."""
        _custom_models[config.name] = config

    @staticmethod
    def list_models() -> list[str]:
        """List all available model names."""
        return sorted({*_BUILTIN_MODELS, *_custom_models})
