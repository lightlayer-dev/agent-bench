"""Tests for configuration file loading."""

import pytest
from pathlib import Path
from agent_bench.config import BenchConfig, ModelConfig, ModelProvider


class TestConfigLoad:
    def test_default_config(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config = BenchConfig.load()
        assert config.models == []
        assert config.default_timeout == 120

    def test_load_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yaml").write_text(
            """
models:
  - name: test-model
    provider: anthropic
    model_id: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY
default_timeout: 60
"""
        )
        config = BenchConfig.load()
        assert len(config.models) == 1
        assert config.models[0].name == "test-model"
        assert config.models[0].provider == ModelProvider.ANTHROPIC
        assert config.default_timeout == 60

    def test_load_explicit_path(self, tmp_path):
        p = tmp_path / "custom.yaml"
        p.write_text(
            """
models:
  - name: custom
    provider: openai
    model_id: gpt-4o
"""
        )
        config = BenchConfig.load(p)
        assert config.models[0].name == "custom"

    def test_load_toml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.toml").write_text(
            """
default_timeout = 90

[[models]]
name = "toml-model"
provider = "anthropic"
model_id = "claude-sonnet-4-20250514"
"""
        )
        config = BenchConfig.load()
        assert config.models[0].name == "toml-model"
        assert config.default_timeout == 90

    def test_auto_discover_yml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yml").write_text("default_timeout: 45\n")
        config = BenchConfig.load()
        assert config.default_timeout == 45

    def test_auto_discover_dotfile(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".agent-bench.yaml").write_text("default_timeout: 33\n")
        config = BenchConfig.load()
        assert config.default_timeout == 33

    def test_yaml_takes_priority(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yaml").write_text("default_timeout: 10\n")
        (tmp_path / "agent-bench.toml").write_text("default_timeout = 20\n")
        config = BenchConfig.load()
        assert config.default_timeout == 10

    def test_get_model(self):
        config = BenchConfig(
            models=[
                ModelConfig(name="a", provider=ModelProvider.ANTHROPIC, model_id="x"),
                ModelConfig(name="b", provider=ModelProvider.OPENAI, model_id="y"),
            ]
        )
        assert config.get_model("b").model_id == "y"

    def test_get_model_not_found(self):
        config = BenchConfig()
        with pytest.raises(ValueError, match="not found"):
            config.get_model("nope")

    def test_empty_yaml(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "agent-bench.yaml").write_text("")
        config = BenchConfig.load()
        assert config.models == []
