"""Data models for analysis results."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckResult:
    """Result from a single check category."""

    name: str
    score: float  # 0.0 - 1.0
    max_score: float = 1.0
    details: dict[str, object] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)
