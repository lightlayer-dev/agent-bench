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
    def test_batch_requires_urls(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # avoid auto-discovering repo's agent-bench.yaml
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


class TestBatchOptions:
    """Tests for batch --threshold, --quiet, --post options."""

    def test_batch_quiet_flag(self, tmp_path):
        runner = CliRunner()
        out = tmp_path / "results"
        result = runner.invoke(
            cli, ["batch", "http://localhost:99999", "-o", str(out), "-q"]
        )
        assert out.exists()
        # Quiet mode should not contain 'Analyzing'
        assert "Analyzing" not in result.output

    def test_batch_threshold_low_site_fails(self, tmp_path):
        runner = CliRunner()
        out = tmp_path / "results"
        # localhost:99999 returns a very low score, threshold should trigger failure
        result = runner.invoke(
            cli, ["batch", "http://localhost:99999", "-o", str(out), "-t", "50"]
        )
        assert result.exit_code == 1
        assert "FAIL" in result.output

    def test_batch_threshold_below_fails(self, tmp_path, monkeypatch):
        """Mock SiteScorer to return a low score, threshold should fail."""
        from unittest.mock import MagicMock
        import json as json_mod

        fake_report = MagicMock()
        fake_report.to_json.return_value = json_mod.dumps(
            {"overall_score": 30, "url": "http://example.com", "checks": []}
        )

        mock_scorer_cls = MagicMock()
        mock_scorer_cls.return_value.run.return_value = fake_report

        monkeypatch.setattr(
            "agent_bench.cli.SiteScorer", mock_scorer_cls, raising=False
        )
        # Need to patch where it's imported
        # Patch inside the function scope by patching the module import
        from unittest.mock import patch

        with patch("agent_bench.analysis.scorer.SiteScorer", mock_scorer_cls):
            runner = CliRunner()
            out = tmp_path / "results"
            result = runner.invoke(
                cli, ["batch", "http://example.com", "-o", str(out), "-t", "50"]
            )
            assert result.exit_code == 1
            assert "FAIL" in result.output

    def test_batch_threshold_above_passes(self, tmp_path):
        """Mock SiteScorer to return a high score, threshold should pass."""
        from unittest.mock import MagicMock, patch
        import json as json_mod

        fake_report = MagicMock()
        fake_report.to_json.return_value = json_mod.dumps(
            {"overall_score": 80, "url": "http://example.com", "checks": []}
        )

        mock_scorer_cls = MagicMock()
        mock_scorer_cls.return_value.run.return_value = fake_report

        with patch("agent_bench.analysis.scorer.SiteScorer", mock_scorer_cls):
            runner = CliRunner()
            out = tmp_path / "results"
            result = runner.invoke(
                cli, ["batch", "http://example.com", "-o", str(out), "-t", "50"]
            )
            assert result.exit_code == 0
            assert "FAIL" not in result.output


class TestBatchConfigSites:
    """Tests for batch reading sites from config."""

    def test_batch_no_urls_no_config_fails(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)  # avoid auto-discovering repo's agent-bench.yaml
        runner = CliRunner()
        out = tmp_path / "results"
        result = runner.invoke(cli, ["batch", "-o", str(out)])
        assert result.exit_code != 0
        assert "No URLs" in result.output

    def test_batch_reads_from_config(self, tmp_path):
        config = tmp_path / "agent-bench.yaml"
        config.write_text("sites:\n  - url: http://localhost:99999\n")
        out = tmp_path / "results"
        runner = CliRunner()
        runner.invoke(cli, ["batch", "--config", str(config), "-o", str(out)])
        # Should run (may error on fetch but shouldn't crash)
        assert out.exists()

    def test_batch_config_with_checks(self, tmp_path):
        from unittest.mock import MagicMock, patch
        import json as json_mod

        config = tmp_path / "agent-bench.yaml"
        config.write_text(
            'sites:\n  - url: http://example.com\n    checks: ["api", "docs"]\n'
        )
        out = tmp_path / "results"

        fake_report = MagicMock()
        fake_report.to_json.return_value = json_mod.dumps(
            {"overall_score": 50, "url": "http://example.com", "checks": []}
        )
        mock_scorer = MagicMock()
        mock_scorer.return_value.run.return_value = fake_report

        with patch("agent_bench.analysis.scorer.SiteScorer", mock_scorer):
            runner = CliRunner()
            result = runner.invoke(
                cli, ["batch", "--config", str(config), "-o", str(out)]
            )
            assert result.exit_code == 0
            # Verify checks were passed
            mock_scorer.assert_called_once_with(
                url="http://example.com", checks=["api", "docs"]
            )

    def test_batch_merges_cli_and_config(self, tmp_path):
        from unittest.mock import MagicMock, patch
        import json as json_mod

        config = tmp_path / "agent-bench.yaml"
        config.write_text("sites:\n  - url: http://config-site.com\n")
        out = tmp_path / "results"

        fake_report = MagicMock()
        fake_report.to_json.return_value = json_mod.dumps(
            {"overall_score": 60, "url": "http://x.com", "checks": []}
        )
        mock_scorer = MagicMock()
        mock_scorer.return_value.run.return_value = fake_report

        with patch("agent_bench.analysis.scorer.SiteScorer", mock_scorer):
            runner = CliRunner()
            result = runner.invoke(
                cli,
                [
                    "batch",
                    "http://cli-site.com",
                    "--config",
                    str(config),
                    "-o",
                    str(out),
                ],
            )
            assert result.exit_code == 0
            assert mock_scorer.call_count == 2

    def test_site_entry_label(self):
        from agent_bench.config import SiteEntry

        s = SiteEntry(url="http://example.com", label="Example")
        assert s.label == "Example"
        assert s.checks is None
