# ============================================================
#  tests/test_benchmark_report.py — testes de BenchmarkReport
#  Resumo + persistência com store em fallback JSON (sem Mongo).
# ============================================================

import os
import shutil
import tempfile
import unittest
from typing import Any

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from tools.benchmarks.report import BenchmarkReport  # noqa: E402
from data.mongodb.store import TaskStore  # noqa: E402


def fake_results() -> list[dict[str, Any]]:
    return [
        {"task_id": "a", "category": "bug", "finished": True,
         "checks_passed": 2, "checks_total": 2, "elapsed_s": 1.5,
         "tool_calls": 3, "retries": 0, "files_created": 2,
         "checks": [], "executor_error": None, "tokens": 10,
         "project_dir": "/tmp/a"},
        {"task_id": "b", "category": "bug", "finished": False,
         "checks_passed": 1, "checks_total": 2, "elapsed_s": 2.5,
         "tool_calls": 5, "retries": 2, "files_created": 1,
         "checks": [], "executor_error": None, "tokens": 20,
         "project_dir": "/tmp/b"},
    ]


class TestBenchmarkReport(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="benchrep_test_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_resumo_metricas(self) -> None:
        summary: dict[str, Any] = BenchmarkReport().summarize(fake_results())
        self.assertEqual(summary["total_tasks"], 2)
        self.assertEqual(summary["finished"], 1)
        self.assertEqual(summary["finish_rate"], 0.5)
        self.assertEqual(summary["avg_elapsed_s"], 2.0)
        self.assertEqual(summary["total_files_created"], 3)

    def test_persistencia_fallback_json(self) -> None:
        store = TaskStore(
            uri="mongodb://127.0.0.1:1", timeout_ms=300,
            state_path=os.path.join(self.dir, "s.json"),
            validations_path=os.path.join(self.dir, "v.json"))
        report = BenchmarkReport(store)
        summary: dict[str, Any] = report.summarize(fake_results())
        report.save(summary)
        saved: list[dict[str, Any]] = store.list_benchmarks(limit=5)
        self.assertEqual(len(saved), 1, "1 doc por modelo (unknown)")
        self.assertEqual(saved[0]["model"], "unknown")
        timeline: list[dict[str, Any]] = saved[0].get("timeline") or []
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["total_tasks"], 2)
        self.assertTrue(os.path.isfile(
            os.path.join(self.dir, "benchmarks.json")))
        store.close()


if __name__ == "__main__":
    unittest.main()