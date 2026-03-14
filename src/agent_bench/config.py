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
