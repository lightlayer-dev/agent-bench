"""JSON Schema for agent-bench analysis results.

Provides a machine-readable schema that describes the output format of
`agent-bench analyze` and `agent-bench batch`. Useful for:
- Dashboard integrations
- CI pipeline parsing
- Third-party tooling
"""

from __future__ import annotations

import json

# Schema version — bump when output format changes
SCHEMA_VERSION = "1.0.0"

ANALYSIS_RESULT_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/LightLayer-dev/agent-bench/blob/main/schema/analysis-result.json",
    "title": "agent-bench Analysis Result",
    "description": "Output from `agent-bench analyze` — a scored evaluation of a website's AI-agent readiness.",
    "version": SCHEMA_VERSION,
    "type": "object",
    "required": ["url", "overall_score", "checks"],
    "properties": {
        "url": {
            "type": "string",
            "format": "uri",
            "description": "The analyzed URL.",
        },
        "overall_score": {
            "type": "number",
            "minimum": 0,
            "maximum": 1,
            "description": "Weighted overall agent-readiness score (0-1).",
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "ISO 8601 timestamp of the analysis.",
        },
        "schema_version": {
            "type": "string",
            "description": "Schema version for forward compatibility.",
        },
        "checks": {
            "type": "array",
            "description": "Individual check results.",
            "items": {
                "type": "object",
                "required": ["name", "score"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Check identifier.",
                        "enum": [
                            "a11y",
                            "api",
                            "auth",
                            "cost",
                            "docs",
                            "errors",
                            "performance",
                            "structure",
                        ],
                    },
                    "score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "description": "Check score (0-1).",
                    },
                    "findings": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Human-readable findings.",
                    },
                    "details": {
                        "type": "object",
                        "description": "Machine-readable details (check-specific).",
                        "additionalProperties": True,
                    },
                },
            },
        },
    },
    "additionalProperties": True,
}

BATCH_RESULT_SCHEMA: dict = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://github.com/LightLayer-dev/agent-bench/blob/main/schema/batch-result.json",
    "title": "agent-bench Batch Result",
    "description": "Output from `agent-bench batch` — an array of analysis results.",
    "version": SCHEMA_VERSION,
    "type": "array",
    "items": ANALYSIS_RESULT_SCHEMA,
}


def get_schema(kind: str = "analysis") -> dict:
    """Get a JSON schema by kind ('analysis' or 'batch')."""
    if kind == "batch":
        return BATCH_RESULT_SCHEMA
    return ANALYSIS_RESULT_SCHEMA


def export_schema(kind: str = "analysis", indent: int = 2) -> str:
    """Export schema as formatted JSON string."""
    return json.dumps(get_schema(kind), indent=indent)


def validate_result(data: dict) -> list[str]:
    """Basic validation of an analysis result against the schema.

    Returns a list of validation errors (empty = valid).
    Does not require jsonschema library — performs structural checks only.
    """
    errors: list[str] = []

    if not isinstance(data, dict):
        return ["Result must be a JSON object"]

    for field in ("url", "overall_score", "checks"):
        if field not in data:
            errors.append(f"Missing required field: {field}")

    if "overall_score" in data:
        score = data["overall_score"]
        if not isinstance(score, (int, float)):
            errors.append(f"overall_score must be a number, got {type(score).__name__}")
        elif not (0 <= score <= 1):
            errors.append(f"overall_score must be 0-1, got {score}")

    if "checks" in data:
        if not isinstance(data["checks"], list):
            errors.append("checks must be an array")
        else:
            for i, check in enumerate(data["checks"]):
                if not isinstance(check, dict):
                    errors.append(f"checks[{i}] must be an object")
                    continue
                if "name" not in check:
                    errors.append(f"checks[{i}] missing 'name'")
                if "score" not in check:
                    errors.append(f"checks[{i}] missing 'score'")
                elif not isinstance(check["score"], (int, float)):
                    errors.append(f"checks[{i}].score must be a number")

    return errors
