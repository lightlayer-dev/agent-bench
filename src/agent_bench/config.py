"""Configuration models for agent-bench."""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, HttpUrl


class ModelProvider(str, Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    CUSTOM = "custom"


class ModelConfig(BaseModel):
    """Configuration for a foundation model."""

    name: str
    provider: ModelProvider
    model_id: str
    api_key_env: str | None = None
    temperature: float = 0.0
    max_tokens: int = 4096


class AdapterType(str, Enum):
    BROWSER_USE = "browser-use"
    PLAYWRIGHT = "playwright"
    CUSTOM = "custom"


class AdapterConfig(BaseModel):
    """Configuration for an agent framework adapter."""

    type: AdapterType
    headless: bool = True
    timeout_seconds: int = 120
    max_steps: int = 50


class AnalysisConfig(BaseModel):
    """Configuration for static site analysis."""

    url: HttpUrl
    checks: list[str] = ["api", "auth", "cost", "docs", "structure", "errors"]
    timeout_seconds: int = 30


class RunConfig(BaseModel):
    """Configuration for a benchmark run."""

    task_file: Path
    model: ModelConfig
    adapter: AdapterConfig
    runs: int = 3
    output_dir: Path = Path("results")


class BenchConfig(BaseModel):
    """Top-level configuration."""

    models: list[ModelConfig] = []
    adapters: list[AdapterConfig] = []
    default_timeout: int = 120

    @classmethod
    def load(cls, path: Path | None = None) -> "BenchConfig":
        """Load config from a file, auto-discovering if path is None.

        Search order: agent-bench.yaml, agent-bench.yml, agent-bench.toml,
        .agent-bench.yaml, .agent-bench.yml
        """
        if path is not None:
            return cls._load_file(path)

        candidates = [
            "agent-bench.yaml",
            "agent-bench.yml",
            "agent-bench.toml",
            ".agent-bench.yaml",
            ".agent-bench.yml",
        ]
        for name in candidates:
            p = Path(name)
            if p.exists():
                return cls._load_file(p)

        return cls()

    @classmethod
    def _load_file(cls, path: Path) -> "BenchConfig":
        """Load config from a specific file."""
        text = path.read_text()
        if path.suffix == ".toml":
            try:
                import tomllib
            except ModuleNotFoundError:
                import tomli as tomllib  # type: ignore[no-redef]
            data = tomllib.loads(text)
        else:
            import yaml
            data = yaml.safe_load(text) or {}
        return cls.model_validate(data)

    def get_model(self, name: str) -> ModelConfig:
        """Look up a model by name."""
        for m in self.models:
            if m.name == name:
                return m
        available = [m.name for m in self.models]
        raise ValueError(
            f"Model '{name}' not found in config. Available: {available}"
        )
