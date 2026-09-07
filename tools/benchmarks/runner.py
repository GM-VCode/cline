# ============================================================
#  tools/benchmarks/runner.py
#  class ModelExecutor  -> ponto de extensão: executa uma instrução
#                          no modelo (hoje stub; depois pluga no
#                          /v1/chat/completions do llama-server local)
#  class BenchmarkRunner -> roda cada BenchmarkTask em um projeto
#                           temporário, mede métricas e valida checks
# ============================================================

import os
import shutil
import tempfile
import time


class ModelExecutor:
    """Executa uma instrução no modelo. STUB plugável.

    Subclasses futuras devem implementar `execute(instruction,
    project_dir)` chamando o llama-server (/v1/chat/completions)
    e aplicando as edições no projeto (via Cline ou API).
    """

    def execute(self, instruction: str, project_dir: str) -> dict:
        raise NotImplementedError("Plugue um executor real do modelo")


class BenchmarkRunner:
    """Roda tarefas do benchmark e coleta métricas por tarefa."""

    def __init__(self, executor: ModelExecutor, tasks: list,
                 work_root: str = None):
        self.executor = executor
        self.tasks = tasks
        self.work_root = work_root or tempfile.gettempdir()

    def _fresh_project(self, task_id: str) -> str:
        """Cria um projeto temporário limpo para a tarefa."""
        project_dir = os.path.join(self.work_root, f"bench_{task_id}")
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)
        os.makedirs(project_dir, exist_ok=True)
        return project_dir

    def _seed_project(self, task, project_dir: str):
        """Semear arquivos iniciais quando a tarefa exige (ex.: bug)."""
        seeds = {
            "004_bug_multi_arquivo": {
                "src/app.py": "from src.utils.helpers import needed\\n\\n\\ndef main():\\n    return needed()\\n",
            },
            "005_feature_com_testes": {
                "string_utils.py": "def slugify(text):\n    return text  # TODO: implementar\n",
            },
            "006_refactor_sem_quebrar": {
                "calc.py": "def add(a, b):\n    return a + b\n",
            },
            "007_interpretar_erro": {
                "main.py": "from calc import add\n\nprint(add(1, 2))\n",
            },
            "009_codigo_e_docs": {
                "calc.py": "def add(a, b):\n    return a + b\n",
            },
            "008_projeto_desconhecido": {
                "src/app.py": "from src.core import process\n\ndef main():\n    return process()\n",
            },
            "010_consertar_incompleto": {
                "calc.py": "def add(a, b, c)\\n    return a + b + c\\n",
            },
        }
        for rel, content in seeds.get(task.task_id, {}).items():
            path = os.path.join(project_dir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

    def run_task(self, task) -> dict:
        """Executa uma tarefa e retorna métricas + resultado dos checks."""
        project_dir = self._fresh_project(task.task_id)
        self._seed_project(task, project_dir)

        started = time.time()
        try:
            response = self.executor.execute(task.instruction, project_dir)
            error = None
        except Exception as exc:  # pragma: no cover
            response, error = None, str(exc)
        elapsed = round(time.time() - started, 2)

        checks = task.run_checks(project_dir)
        passed = sum(1 for _, ok, _ in checks if ok)
        finished = error is None and passed == len(checks)

        files_changed = self._count_files(project_dir)
        return {
            "task_id": task.task_id,
            "category": task.category,
            "finished": finished,
            "executor_error": error,
            "checks_total": len(checks),
            "checks_passed": passed,
            "checks": [(n, o, m) for n, o, m in checks],
            "files_created": files_changed,
            "elapsed_s": elapsed,
            "tool_calls": (response or {}).get("tool_calls", 0),
            "retries": (response or {}).get("retries", 0),
            "tokens": (response or {}).get("tokens", 0),
            "project_dir": project_dir,
        }

    @staticmethod
    def _count_files(project_dir: str) -> int:
        total = 0
        for _root, _dirs, files in os.walk(project_dir):
            total += len(files)
        return total

    def run_all(self) -> list:
        return [self.run_task(t) for t in self.tasks]