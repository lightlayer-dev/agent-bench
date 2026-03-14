"""Tests for results storage and comparison."""

import json
from agent_bench.results.store import ResultStore
from agent_bench.results.compare import compare_runs


class TestResultStore:
    def test_save_and_load(self, tmp_path):
        from agent_bench.runner.metrics import AggregateMetrics, RunMetrics

        agg = AggregateMetrics(
            task_name="test-task",
            model_name="claude-sonnet",
            adapter_name="browser-use",
        )
        metrics = RunMetrics(
            task_name="test-task",
            model_name="claude-sonnet",
            adapter_name="browser-use",
            run_index=0,
        )
        metrics.success = True
        metrics.steps_taken = 3
        metrics.input_tokens = 1000
        metrics.output_tokens = 200
        agg.runs.append(metrics)

        store = ResultStore(tmp_path)
        filepath = store.save([agg])

        assert filepath.exists()
        data = store.load(filepath)
        assert data["results"][0]["task"] == "test-task"
        assert data["results"][0]["model"] == "claude-sonnet"

    def test_list_results(self, tmp_path):
        store = ResultStore(tmp_path)
        assert store.list_results() == []

        # Create some fake result files
        (tmp_path / "bench_20260314_120000.json").write_text("{}")
        (tmp_path / "bench_20260314_130000.json").write_text("{}")
        (tmp_path / "unrelated.txt").write_text("")

        results = store.list_results()
        assert len(results) == 2
        # Should be reverse sorted (newest first)
        assert "130000" in results[0].name

    def test_creates_output_dir(self, tmp_path):
        new_dir = tmp_path / "nested" / "results"
        ResultStore(new_dir)
        assert new_dir.exists()


class TestComparison:
    def _make_result_file(self, tmp_path, name, task, model, adapter, success_rate):
        data = {
            "timestamp": "20260314_120000",
            "results": [{
                "task": task,
                "model": model,
                "adapter": adapter,
                "success_rate": success_rate,
                "avg_steps": 5.0,
                "avg_time": 10.0,
                "avg_cost": 0.05,
            }],
        }
        filepath = tmp_path / name
        filepath.write_text(json.dumps(data))
        return filepath

    def test_compare_runs(self, tmp_path):
        f1 = self._make_result_file(tmp_path, "a.json", "search", "claude", "browser-use", 0.8)
        f2 = self._make_result_file(tmp_path, "b.json", "search", "gpt-4o", "browser-use", 0.6)

        comparison = compare_runs([f1, f2])
        assert len(comparison.rows) == 2
        # Sorted by task then success rate desc
        assert comparison.rows[0].success_rate == 0.8

    def test_render_table(self, tmp_path):
        f1 = self._make_result_file(tmp_path, "a.json", "search", "claude", "browser-use", 0.8)
        comparison = compare_runs([f1])
        table = comparison.render("table")
        assert "search" in table
        assert "claude" in table

    def test_render_markdown(self, tmp_path):
        f1 = self._make_result_file(tmp_path, "a.json", "search", "claude", "browser-use", 0.8)
        comparison = compare_runs([f1])
        md = comparison.render("markdown")
        assert "| search |" in md

    def test_render_json(self, tmp_path):
        f1 = self._make_result_file(tmp_path, "a.json", "search", "claude", "browser-use", 0.8)
        comparison = compare_runs([f1])
        data = json.loads(comparison.render("json"))
        assert len(data) == 1
        assert data[0]["task"] == "search"

    def test_empty_comparison(self):
        comparison = compare_runs([])
        assert len(comparison.rows) == 0
