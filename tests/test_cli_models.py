"""Tests for CLI models and batch commands."""

from click.testing import CliRunner
from agent_bench.cli import cli


class TestModelsCommand:
    def test_lists_builtin_models(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["models"])
        assert result.exit_code == 0
        assert "claude-sonnet" in result.output
        assert "gpt-4o" in result.output
        assert "gemini-pro" in result.output

    def test_shows_provider(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["models"])
        assert "anthropic" in result.output
        assert "openai" in result.output
        assert "google" in result.output


class TestBatchCommand:
    def test_batch_requires_urls(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["batch"])
        assert result.exit_code != 0

    def test_batch_creates_output_dir(self, tmp_path):
        runner = CliRunner()
        out = tmp_path / "results"
        # Use a URL that will fail but test the CLI flow
        result = runner.invoke(cli, ["batch", "http://localhost:99999", "-o", str(out)])
        # Should handle errors gracefully
        assert result.exit_code == 0
        assert out.exists()
