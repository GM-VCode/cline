# ============================================================
#  tools/benchmarks/run.py — entry point do benchmark
#  Roda as tarefas padronizadas, gera o resumo e PERSISTE no
#  MongoDB real (coleção benchmark_runs) ou fallback JSON.
#
#  Uso:
#    .venv\\Scripts\\python.exe tools\\benchmarks\\run.py
#
#  O executor default é o LocalExecutor (resolve as tarefas de
#  forma determinística para validar o pipeline). Para medir o
#  modelo real, plugue um ModelExecutor que chama o llama-server.
# ============================================================

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.benchmarks.runner import BenchmarkRunner, ModelExecutor  # noqa: E402
from tools.benchmarks.tasks import default_catalog  # noqa: E402
from tools.benchmarks.report import BenchmarkReport  # noqa: E402
from data.mongodb.store import TaskStore  # noqa: E402


class LocalExecutor(ModelExecutor):
    """Executor local: resolve as tarefas escrevendo os arquivos
    esperados (mesmo comportamento do FakeExecutor dos testes).
    Serve para validar o pipeline de ponta a ponta sem o modelo."""

    def execute(self, instruction, project_dir):
        task_id = os.path.basename(project_dir).replace("bench_", "")
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


def main() -> int:
    runner = BenchmarkRunner(LocalExecutor(), default_catalog())
    results = runner.run_all()
    report = BenchmarkReport(TaskStore())
    summary = report.save(report.summarize(results))
    report.print_summary(summary)
    # Confirmar persistência
    store = TaskStore()
    saved = store.list_benchmarks(limit=1)
    store.close()
    n = len(saved) if saved else 0
    print(f"  persistido: {n} corrida(s) em benchmark_runs")
    return 0


if __name__ == "__main__":
    sys.exit(main())