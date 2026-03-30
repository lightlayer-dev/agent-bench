"""Tests for CLI commands."""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

from click.testing import CliRunner

from agent_bench.cli import cli


class _MockDashboardHandler(BaseHTTPRequestHandler):
    """Mock dashboard that accepts scan POSTs."""

    received = []

    def do_POST(self):
        length = int(self.headers["Content-Length"])
        body = json.loads(self.rfile.read(length))
        _MockDashboardHandler.received.append(body)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"id": 42, "site_id": 1}).encode())

    def log_message(self, *args):
        pass  # Suppress server logs


class TestAnalyzeDashboardPost:
    def test_post_flag_sends_to_dashboard(self):
        _MockDashboardHandler.received.clear()
        server = HTTPServer(("127.0.0.1", 0), _MockDashboardHandler)
        port = server.server_address[1]
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "analyze",
                "https://httpbin.org",
                "--post",
                f"http://127.0.0.1:{port}",
                "--source",
                "ci",
                "--quiet",
            ],
        )

        thread.join(timeout=5)
        server.server_close()

        assert result.exit_code == 0
        assert len(_MockDashboardHandler.received) == 1
        payload = _MockDashboardHandler.received[0]
        assert payload["url"] == "https://httpbin.org"
        assert payload["source"] == "ci"
        assert "overall_score" in payload
        assert "checks" in payload

    def test_post_flag_failure_doesnt_crash(self):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "analyze",
                "https://httpbin.org",
                "--post",
                "http://127.0.0.1:1",  # Nothing listening
                "--quiet",
            ],
        )
        # Should still exit 0 (post failure is non-fatal)
        assert result.exit_code == 0


class TestAnalyzeThreshold:
    def test_threshold_pass(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["analyze", "https://httpbin.org", "--threshold", "0.0"]
        )
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_threshold_fail(self):
        runner = CliRunner()
        result = runner.invoke(
            cli, ["analyze", "https://httpbin.org", "--threshold", "1.0"]
        )
        assert result.exit_code == 1
        assert "FAIL" in result.output


class TestAnalyzeQuiet:
    def test_quiet_suppresses_output(self):
        runner = CliRunner()
        result = runner.invoke(cli, ["analyze", "https://httpbin.org", "--quiet"])
        assert result.exit_code == 0
        assert result.output.strip() == ""
