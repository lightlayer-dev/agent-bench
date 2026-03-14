"""Task definitions — what an agent should do on a website."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class TaskStep(BaseModel):
    """A single step in a task."""

    action: str
    params: dict[str, Any] = {}
    description: str | None = None


class SuccessCriterion(BaseModel):
    """How to determine if a task was completed successfully."""

    type: str  # "element_exists", "url_matches", "text_contains", "custom"
    value: str
    description: str | None = None


class Task(BaseModel):
    """A benchmark task definition."""

    name: str
    site: str
    description: str
    steps: list[TaskStep] = []
    success_criteria: list[SuccessCriterion] = []
    tags: list[str] = []
    difficulty: str = "medium"  # easy, medium, hard
    expected_time_seconds: int | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> Task:
        """Load a task from a YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

    @classmethod
    def from_yaml_multi(cls, path: Path) -> list[Task]:
        """Load multiple tasks from a YAML file (multi-document)."""
        tasks = []
        with open(path) as f:
            for doc in yaml.safe_load_all(f):
                if doc:
                    tasks.append(cls(**doc))
        return tasks
