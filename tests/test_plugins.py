"""Tests for the plugin system and checks CLI command."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from agent_bench.analysis.checks import BaseCheck
from agent_bench.analysis.models import CheckResult
from agent_bench.analysis.scorer import _get_builtin_checks, _get_check_registry
from agent_bench.cli import cli


class DummyCheck(BaseCheck):
    """A dummy check for testing plugins."""

    name = "dummy"

    def execute(self) -> CheckResult:
        return CheckResult(name=self.name, score=1.0, findings=["All good"])


class TestBuiltinChecks:
    def test_has_all_builtins(self):
        builtins = _get_builtin_checks()
        assert set(builtins.keys()) == {
            "a11y",
            "a2a",
            "agents_txt",
            "api",
            "auth",
            "cost",
            "docs",
            "errors",
            "performance",
            "structure",
            "x402",
        }

    def test_registry_includes_builtins(self):
        registry = _get_check_registry()
        assert "api" in registry
        assert "structure" in registry


class TestPluginDiscovery:
    def _make_ep(self, name, cls=None, error=None):
        ep = MagicMock()
        ep.name = name
        if error:
            ep.load.side_effect = error
        else:
            ep.load.return_value = cls
        return ep

    def _mock_entry_points(self, eps_list):
        """Mock entry_points for Python 3.12+ (keyword group= returns list)."""

        def fake_entry_points(*, group=None):
            if group == "agent_bench.checks":
                return eps_list
            return []

        return fake_entry_points

    def test_plugin_added_to_registry(self):
        ep = self._make_ep("dummy", DummyCheck)
        with patch("importlib.metadata.entry_points", self._mock_entry_points([ep])):
            registry = _get_check_registry()
            assert "dummy" in registry
            assert registry["dummy"] is DummyCheck

    def test_broken_plugin_skipped(self):
        ep = self._make_ep("broken", error=ImportError("no such module"))
        with patch("importlib.metadata.entry_points", self._mock_entry_points([ep])):
            registry = _get_check_registry()
            assert "broken" not in registry
            assert "api" in registry

    def test_plugin_overrides_builtin(self):
        ep = self._make_ep("api", DummyCheck)
        with patch("importlib.metadata.entry_points", self._mock_entry_points([ep])):
            registry = _get_check_registry()
            assert registry["api"] is DummyCheck


class TestChecksCommand:
    def test_lists_builtins(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["checks"])
        assert result.exit_code == 0
        assert "Built-in checks" in result.output
        assert "api" in result.output
        assert "structure" in result.output
        assert "a11y" in result.output

    def test_shows_no_plugins_message(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["checks"])
        assert "No plugin checks installed" in result.output
