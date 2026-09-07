# ============================================================
#  tests/test_benchmarks.py — testes do benchmark
#  Usa um executor FAKE que "resolve" as tarefas escrevendo os
#  arquivos esperados: nada de modelo real, Mongo ou rede.
# ============================================================

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.benchmarks.runner import BenchmarkRunner, ModelExecutor  # noqa: E402
from tools.benchmarks.tasks import default_catalog  # noqa: E402


class FakeExecutor(ModelExecutor):
    """Executor fake: cria os arquivos esperados da tarefa."""

    def __init__(self, fail_task_ids=()):
        self.fail_task_ids = set(fail_task_ids)
        self.calls = []

    def execute(self, instruction, project_dir):
        self.calls.append(instruction)
        # descobre task_id pelo nome da pasta (bench_<id>)
        task_id = os.path.basename(project_dir).replace("bench_", "")
        if task_id in self.fail_task_ids:
            return {"tool_calls": 1, "retries": 1, "tokens": 10}
        for task in default_catalog():
            if task.task_id == task_id:
                for rel in task.expected_files:
                    path = os.path.join(project_dir, rel)
                    os.makedirs(os.path.dirname(path), exist_ok=True)
                    if rel.startswith("test_"):
                        content = ("import unittest\n\n\n"
                                   "class T(unittest.TestCase):\n"
                                   "    def test_ok(self):\n"
                                   "        self.assertTrue(True)\n")
                    elif rel.endswith(".py"):
                        content = ("def add(a, b, c):\n"
                                   "    def _sum(a, b, c):\n"
                                   "        return a + b + c\n"
                                   "    return _sum(a, b, c)\n"
                                   "def div(a, b):\n"
                                   "    return a / b\n")
                    else:
                        content = "docs: como usar a funcao add\n"
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)
        return {"tool_calls": 3, "retries": 0, "tokens": 100}


def local_tasks():
    """Apenas tarefas sem seeds externos complexos, para testes rápidos."""
    return [t for t in default_catalog()
            if t.task_id in ("001_criar_funcao", "002_editar_funcao",
                             "005_feature_com_testes",
                             "009_codigo_e_docs")]


class TestBenchmarkRunner(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="bench_test_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_todas_passam_com_executor_fake(self):
        runner = BenchmarkRunner(FakeExecutor(), local_tasks(),
                                 work_root=self.dir)
        results = runner.run_all()
        self.assertEqual(len(results), 4)
        for r in results:
            self.assertTrue(r["finished"], f"{r['task_id']} não terminou")
            self.assertEqual(r["checks_passed"], r["checks_total"])

    def test_tarefa_falha_registra_metricas(self):
        runner = BenchmarkRunner(FakeExecutor(fail_task_ids={"001_criar_funcao"}),
                                 [t for t in local_tasks()
                                  if t.task_id == "001_criar_funcao"],
                                 work_root=self.dir)
        results = runner.run_all()
        r = results[0]
        self.assertFalse(r["finished"])
        self.assertEqual(r["retries"], 1)
        self.assertLess(r["checks_passed"], r["checks_total"])

    def test_metricas_coletadas(self):
        runner = BenchmarkRunner(FakeExecutor(), local_tasks()[:1],
                                 work_root=self.dir)
        r = runner.run_all()[0]
        self.assertIn("elapsed_s", r)
        self.assertIn("tool_calls", r)
        self.assertIn("tokens", r)
        self.assertEqual(r["tool_calls"], 3)

    def test_projeto_fresh_a_cada_run(self):
        runner = BenchmarkRunner(FakeExecutor(), local_tasks()[:1],
                                 work_root=self.dir)
        r1 = runner.run_all()
        n1 = r1[0]["files_created"]
        r2 = runner.run_all()
        self.assertEqual(r2[0]["files_created"], n1)  # sem duplicar


if __name__ == "__main__":
    unittest.main()