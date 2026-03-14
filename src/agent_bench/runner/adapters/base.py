"""Base adapter interface for agent frameworks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_bench.config import ModelConfig
    from agent_bench.runner.metrics import RunMetrics
    from agent_bench.runner.task import Task


class BaseAdapter(ABC):
    """Abstract base class for agent framework adapters.

    Each adapter wraps a specific agent framework (browser-use, Playwright, etc.)
    and provides a uniform interface for running tasks and collecting metrics.
    """

    name: str = "base"

    def __init__(self, model_config: ModelConfig) -> None:
        self.model_config = model_config

    @abstractmethod
    def run_task(self, task: Task, metrics: RunMetrics) -> bool:
        """Run a task and return True if successful.

        The adapter should:
        1. Set up the agent with the configured model
        2. Execute the task steps (or let the agent figure it out from the description)
        3. Record steps in metrics via metrics.record_step()
        4. Evaluate success criteria
        5. Return True if all success criteria are met
        """
        ...

    def setup(self) -> None:
        """Optional setup (e.g., launch browser)."""

    def teardown(self) -> None:
        """Optional cleanup."""


# Adapter registry
_ADAPTERS: dict[str, type[BaseAdapter]] = {}


def register_adapter(cls: type[BaseAdapter]) -> type[BaseAdapter]:
    """Register an adapter class."""
    _ADAPTERS[cls.name] = cls
    return cls


def get_adapter(name: str, model_config: ModelConfig) -> BaseAdapter:
    """Get an adapter instance by name."""
    if name not in _ADAPTERS:
        available = ", ".join(_ADAPTERS.keys()) or "none"
        raise ValueError(f"Unknown adapter '{name}'. Available: {available}")
    return _ADAPTERS[name](model_config)
