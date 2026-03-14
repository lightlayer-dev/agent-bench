"""Tests for run command config wiring."""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from agent_bench.cli import cli
from agent_bench.config import BenchConfig, ModelConfig, ModelProvider
from agent_bench.models.registry import ModelRegistry, _custom_models


@pytest.fixture(autouse=True)
def clean_custom_models():
    """Clear custom models between tests."""
    _custom_models.clear()
    yield
    _custom_models.clear()


class TestConfigModelRegistration:
    def test_config_models_registered(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yaml").write_text("""
models:
  - name: my-custom-model
    provider: anthropic
    model_id: claude-test
    api_key_env: TEST_KEY
""")
        config = BenchConfig.load()
        for m in config.models:
            ModelRegistry.register(m)

        model = ModelRegistry.get("my-custom-model")
        assert model.model_id == "claude-test"
        assert model.provider == ModelProvider.ANTHROPIC

    def test_config_overrides_builtin(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yaml").write_text("""
models:
  - name: claude-sonnet
    provider: anthropic
    model_id: claude-sonnet-custom
    temperature: 0.5
""")
        config = BenchConfig.load()
        for m in config.models:
            ModelRegistry.register(m)

        # Custom takes priority
        model = ModelRegistry.get("claude-sonnet")
        assert model.model_id == "claude-sonnet-custom"
        assert model.temperature == 0.5

    def test_builtin_models_still_available(self):
        model = ModelRegistry.get("gpt-4o")
        assert model.provider == ModelProvider.OPENAI


class TestModelsCommand:
    def test_lists_builtins(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0
        assert "claude-sonnet" in result.output
        assert "gpt-4o" in result.output

    def test_lists_config_models(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yaml").write_text("""
models:
  - name: local-llama
    provider: custom
    model_id: llama-3-70b
""")
        runner = CliRunner()
        result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0
        assert "local-llama" in result.output
        assert "From config" in result.output


class TestRunCommand:
    def test_run_with_config_model(self, tmp_path, monkeypatch):
        """Test that run command loads config and can resolve custom models."""
        monkeypatch.chdir(tmp_path)

        # Create config with custom model
        (tmp_path / "agent-bench.yaml").write_text("""
models:
  - name: test-model
    provider: anthropic
    model_id: claude-test
    api_key_env: ANTHROPIC_API_KEY
""")

        # Create a simple task file
        (tmp_path / "task.yaml").write_text("""
name: test-task
site: https://example.com
description: Test task
""")

        runner = CliRunner()
        # This will fail at the adapter level (no real browser), but it should
        # get past config/model resolution
        result = runner.invoke(cli, ["run", "task.yaml", "-m", "test-model", "-a", "custom", "-n", "1"])
        # Should not fail with "Unknown model"
        assert "Unknown model" not in (result.output or "")

    def test_run_unknown_model_fails(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "task.yaml").write_text("""
name: test
site: https://example.com
description: Test
""")
        runner = CliRunner()
        result = runner.invoke(cli, ["run", "task.yaml", "-m", "nonexistent-model", "-n", "1"])
        assert result.exit_code != 0 or "Unknown model" in (result.output or str(result.exception))
