"""Tests for JSON Schema export and validation."""

from __future__ import annotations

import json

from click.testing import CliRunner

from agent_bench.analysis.schema import (
    SCHEMA_VERSION,
    export_schema,
    get_schema,
    validate_result,
)
from agent_bench.cli import cli


class TestSchema:
    def test_analysis_schema_valid_json(self):
        s = get_schema("analysis")
        assert s["type"] == "object"
        assert "url" in s["properties"]

    def test_batch_schema_is_array(self):
        s = get_schema("batch")
        assert s["type"] == "array"

    def test_export_is_json(self):
        text = export_schema("analysis")
        data = json.loads(text)
        assert data["title"] == "agent-bench Analysis Result"

    def test_schema_version(self):
        assert SCHEMA_VERSION == "1.0.0"


class TestValidation:
    def test_valid_result(self):
        data = {
            "url": "https://example.com",
            "overall_score": 0.5,
            "checks": [{"name": "api", "score": 0.6}],
        }
        assert validate_result(data) == []

    def test_missing_url(self):
        data = {"overall_score": 0.5, "checks": []}
        errors = validate_result(data)
        assert any("url" in e for e in errors)

    def test_missing_checks(self):
        data = {"url": "https://x.com", "overall_score": 0.5}
        errors = validate_result(data)
        assert any("checks" in e for e in errors)

    def test_score_out_of_range(self):
        data = {"url": "https://x.com", "overall_score": 1.5, "checks": []}
        errors = validate_result(data)
        assert any("0-1" in e for e in errors)

    def test_check_missing_name(self):
        data = {"url": "https://x.com", "overall_score": 0.5, "checks": [{"score": 0.5}]}
        errors = validate_result(data)
        assert any("name" in e for e in errors)

    def test_check_missing_score(self):
        data = {"url": "https://x.com", "overall_score": 0.5, "checks": [{"name": "api"}]}
        errors = validate_result(data)
        assert any("score" in e for e in errors)

    def test_not_a_dict(self):
        errors = validate_result("not a dict")
        assert len(errors) == 1


class TestSchemaCli:
    def test_schema_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["schema"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "properties" in data

    def test_schema_batch(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["schema", "batch"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["type"] == "array"

    def test_schema_to_file(self, tmp_path):
        out = tmp_path / "schema.json"
        runner = CliRunner()
        result = runner.invoke(cli, ["schema", "-o", str(out)])
        assert result.exit_code == 0
        assert out.exists()

    def test_validate_valid_file(self, tmp_path):
        f = tmp_path / "result.json"
        f.write_text(json.dumps({"url": "https://x.com", "overall_score": 0.5, "checks": []}))
        runner = CliRunner()
        result = runner.invoke(cli, ["schema", "--validate", str(f)])
        assert result.exit_code == 0
        assert "Valid" in result.output

    def test_validate_invalid_file(self, tmp_path):
        f = tmp_path / "bad.json"
        f.write_text(json.dumps({"overall_score": 2.0}))
        runner = CliRunner()
        result = runner.invoke(cli, ["schema", "--validate", str(f)])
        assert result.exit_code == 1
