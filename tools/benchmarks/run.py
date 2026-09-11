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
from typing import Any

# Força UTF-8 no stdout para evitar UnicodeEncodeError (cp1252 no Windows CMD)
_reconfigure = getattr(sys.stdout, "reconfigure", None)
if callable(_reconfigure) and sys.stdout.encoding != "utf-8":
    try:
        _reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # pragma: no cover
        pass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()

from tools.benchmarks.runner import BenchmarkRunner, ModelExecutor  # noqa: E402
from tools.benchmarks.tasks import default_catalog  # noqa: E402
from tools.benchmarks.report import BenchmarkReport  # noqa: E402
from tools.benchmarks.executor_llama import LlamaExecutor  # noqa: E402
from data.mongodb.store import TaskStore  # noqa: E402
from project_path import Config  # noqa: E402


def model_key() -> str:
    """Nome único do modelo atual (do gguf): ex. 'Q8_0'."""
    arquivo = os.path.splitext(os.path.basename(Config().MODEL_PATH))[0]
    return arquivo.split("-")[-1].strip() or "unknown"


class LocalExecutor(ModelExecutor):
    """Executor local: resolve as tarefas escrevendo os arquivos
    esperados (mesmo comportamento do FakeExecutor dos testes).
    Serve para validar o pipeline de ponta a ponta sem o modelo."""

    def execute(
        self,
        instruction: str,
        project_dir: str,
    ) -> dict[str, Any]:
        _ = instruction
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
    import argparse
    ap = argparse.ArgumentParser(description="Benchmark do agente")
    ap.add_argument("--real", action="store_true",
                    help="usa o modelo real (/v1) em vez do stub local")
    ap.add_argument("--max-actions", type=int, default=None,
                    help="ativa o modo iterativo 11c (ex.: 8)")
    ap.add_argument("--attempts", type=int, default=2,
                    help="tentativas por tarefa com feedback dos checks")
    args = ap.parse_args()
    # `--real` mede o modelo de verdade (chama /v1); senão usa LocalExecutor
    use_real = args.real
    executor = (LlamaExecutor() if use_real else LocalExecutor())
    # projetos de debug de cada tarefa ficam em <repo>/temp/bench_<id>
    # (aparecem lá para inspeção; apagados/recriados a cada corrida)
    work_root = ProjectPath.join("temp")
    os.makedirs(work_root, exist_ok=True)
    runner = BenchmarkRunner(executor, default_catalog(),
                             work_root=work_root,
                             max_attempts=args.attempts,
                             max_actions=args.max_actions)
    results = runner.run_all()
    store = TaskStore(model_name=model_key())
    report = BenchmarkReport(store)
    summary = report.save(report.summarize(results))
    report.print_summary(summary)
    # Confirmar persistência (na coleção do modelo atual)
    saved = store.list_benchmarks(limit=1)
    store.close()
    n = len(saved) if saved else 0
    print(f"  persistido: {n} corrida(s) em benchmark_runs_{model_key()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())