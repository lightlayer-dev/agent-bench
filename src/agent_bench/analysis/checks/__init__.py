"""Individual analysis check modules."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_bench.analysis.scorer import CheckResult


class BaseCheck(ABC):
    """Base class for all analysis checks."""

    name: str = "base"

    def __init__(self, url: str) -> None:
        self.url = url

    @abstractmethod
    def execute(self) -> CheckResult:
        """Run the check and return a scored result."""
        ...
