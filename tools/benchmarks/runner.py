# ============================================================
#  tools/benchmarks/runner.py
#  class ModelExecutor  -> ponto de extensão: executa uma instrução
#                          no modelo (hoje stub; depois pluga no
#                          /v1/chat/completions do llama-server local)
#  class BenchmarkRunner -> roda cada BenchmarkTask em um projeto
#                           temporário, mede métricas e valida checks
# ============================================================

import json
import os
import shutil
import tempfile
import time
from typing import Any, TYPE_CHECKING

from app.agent.debug import get_benchmark_logger
from tools.benchmarks.seeds import BenchmarkProjectSeeder
from tools.benchmarks.tasks.core import BenchmarkTask, CheckResult

if TYPE_CHECKING:  # só p/ anotações (import real é lazy no __init__)
    from app.agent.checks import CheckRunner


class ModelExecutor:
    """Executa uma instrução no modelo. STUB plugável.

    Subclasses futuras devem implementar `execute(instruction,
    project_dir)` chamando o llama-server (/v1/chat/completions)
    e aplicando as edições no projeto (via Cline ou API).
    """

    def execute(self, instruction: str, project_dir: str) -> dict[str, Any]:
        raise NotImplementedError("Plugue um executor real do modelo")

    def execute_with_feedback(self, instruction: str, project_dir: str,
                              feedback: str) -> dict[str, Any]:
        """2.ª tentativa: recebe o feedback dos checks que falharam.
        Default: delega para execute (executores simples ignoram)."""
        return self.execute(instruction, project_dir)

    def execute_action(
        self,
        prompt: str,
        project_dir: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        """Adaptador para o modo iterativo de ações.

        Executores simples ainda podem implementar apenas ``execute``;
        executores interativos podem sobrescrever este método.
        """
        _ = history
        return self.execute(prompt, project_dir)


class BenchmarkRunner:
    """Roda tarefas do benchmark e coleta métricas por tarefa."""

    def __init__(self, executor: ModelExecutor, tasks: list[BenchmarkTask],
                 work_root: str | None = None, max_attempts: int = 2,
                 max_actions: int | None = None) -> None:
        self.executor = executor
        self.tasks = tasks
        self.work_root = work_root or tempfile.gettempdir()
        self.max_attempts = max(1, max_attempts)
        self.max_actions = max_actions  # 11c: None = ciclo clássico
        self.seeder = BenchmarkProjectSeeder()
        self._checks: "CheckRunner | None" = None
        if max_actions is not None:
            from app.agent.checks import CheckRunner
            self._checks = CheckRunner(timeout=120)

    def _fresh_project(self, task_id: str) -> str:
        """Cria um projeto temporário limpo para a tarefa."""
        project_dir = os.path.join(self.work_root, f"bench_{task_id}")
        if os.path.isdir(project_dir):
            shutil.rmtree(project_dir, ignore_errors=True)
        os.makedirs(project_dir, exist_ok=True)
        return project_dir

    def _dump_debug(self, project_dir: str, executor: ModelExecutor,
                    task_id: str, checks: list[CheckResult]) -> None:
        """Deixa o debug VISÍVEL na pasta da tarefa.

        _debug_resposta.json: TODAS as respostas brutas (1 por tentativa)
        + a resposta interpretada (files/edits/run) + erros de edição —
        cada falha do modelo fica visível, não só a última.
        _debug_checks.txt: veredito de cada check.
        Nunca levanta — debug não pode quebrar o run.
        """
        try:
            raws = getattr(executor, "raw_history", None) or []
            last = getattr(executor, "last_raw", None)
            brutas = raws if (raws or last is None) else [last]
            dump: dict[str, Any] = {
                "task": task_id,
                "tentativas": len(brutas),
                "respostas_brutas": brutas,
            }
            parsed = getattr(executor, "last_parsed", None)
            if parsed is not None:
                dump["resposta_interpretada"] = parsed
            path = os.path.join(project_dir, "_debug_resposta.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(dump, f, ensure_ascii=False, indent=2,
                          default=str)
            lines = [f"{n}: {'OK' if ok else 'FAIL'} — {m}"
                     for n, ok, m in checks]
            path = os.path.join(project_dir, "_debug_checks.txt")
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"task: {task_id}\n" + "\n".join(lines) + "\n")
        except OSError as exc:  # pragma: no cover — debug não quebra o run
            if log := get_benchmark_logger():
                log.warn(f"debug dump falhou em {project_dir}: {exc}")

    def run_task(self, task: BenchmarkTask) -> dict[str, Any]:
        """Executa uma tarefa e retorna métricas + resultado dos checks."""
        project_dir = self._fresh_project(task.task_id)
        self.seeder.seed(task, project_dir)
        log = get_benchmark_logger()
        if log:
            log.info(f"TASK {task.task_id} [{task.category}] "
                     f"instruction={task.instruction[:80]!r} "
                     f"project_dir={project_dir}")
            log.debug(f"BEGIN {task.task_id}")

        started = time.time()
        retries = 0
        response: dict[str, Any] | None = None
        error: str | None = None
        checks: list[CheckResult] = []
        # 11c: modo iterativo — ActionLoop em vez do ciclo clássico
        if self.max_actions is not None:
            from app.agent.runner.actions import ActionLoop
            checks_runner = self._checks
            if checks_runner is None:
                raise RuntimeError("CheckRunner não inicializado")
            for cycle in range(1, self.max_attempts + 1):
                loop = ActionLoop(self.executor, checks_runner, project_dir,
                                  check_cmd=[],  # checks são callables
                                  max_actions=self.max_actions)
                if cycle > 1:
                    # retry: o erro real dos checks entra como observação 0
                    fb = self._format_feedback(checks)
                    loop.history.append(
                        {"action": "retry",
                         "observation": "Tentativa anterior falhou:\n" + fb})
                    retries += 1
                response = loop.run(task.instruction)
                checks = task.run_checks(project_dir)
                if all(ok for _, ok, _ in checks):
                    break
        else:
            for attempt in range(1, self.max_attempts + 1):
                try:
                    if attempt == 1:
                        response = self.executor.execute(task.instruction,
                                                         project_dir)
                        error = None
                    else:
                        feedback = self._format_feedback(checks)
                        response = self.executor.execute_with_feedback(
                            task.instruction, project_dir, feedback)
                        error = None
                        retries += 1
                except Exception as exc:  # pragma: no cover
                    response = None
                    error = str(exc) or type(exc).__name__
                    # hiccup transitório: consome a tentativa, não a tarefa
                    if attempt < self.max_attempts:
                        continue
                    break
                checks = task.run_checks(project_dir)
                if all(ok for _, ok, _ in checks):
                    break
            elapsed = round(time.time() - started, 2)
            passed = sum(1 for _, ok, _ in checks if ok)
            finished = error is None and passed == len(checks)
            files_changed = self._count_files(project_dir)
            result = {
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
                "retries": retries,
                "tokens": (response or {}).get("tokens", 0),
                "project_dir": project_dir,
            }
            self._dump_debug(project_dir, self.executor, task.task_id,
                             checks)
            if log:
                log.info(f"RESULT {task.task_id} finished={result['finished']} "
                         f"checks={result['checks_passed']}/"
                         f"{result['checks_total']} retries={retries} "
                         f"elapsed_s={result['elapsed_s']} "
                         f"executor_error={result['executor_error']!r}")
            return result

        # modo iterativo (11c)
        elapsed = round(time.time() - started, 2)
        passed = sum(1 for _, ok, _ in checks if ok)
        # métrica do benchmark = checks; 'finished' do loop é secundário
        # (orçamento estourado com checks verdes continua sendo acerto)
        finished = passed == len(checks)
        result = {
            "task_id": task.task_id,
            "category": task.category,
            "finished": finished,
            "executor_error": ("" if finished
                               else ((response or {}).get("error") or "")),
            "checks_total": len(checks),
            "checks_passed": passed,
            "checks": [(n, o, m) for n, o, m in checks],
            "files_created": self._count_files(project_dir),
            "elapsed_s": elapsed,
            "tool_calls": (response or {}).get("actions_used", 0),
            "retries": 0,
            "tokens": (response or {}).get("tokens", 0),
            "project_dir": project_dir,
        }
        self._dump_debug(project_dir, self.executor, task.task_id, checks)
        if log:
            log.info(f"RESULT {task.task_id} finished={result['finished']} "
                     f"checks={result['checks_passed']}/"
                     f"{result['checks_total']} retries=0 "
                     f"elapsed_s={result['elapsed_s']} "
                     f"executor_error={result['executor_error']!r}")
        return result

    @staticmethod
    def _format_feedback(checks: list[CheckResult]) -> str:
        """Monta o feedback com os checks que falharam (2.ª tentativa)."""
        lines = ["Sua resposta anterior não passou na validação. Falhas:"]
        for name, ok, msg in checks:
            if not ok:
                lines.append(f"- {name}: {msg}")
        lines.append("Corrija os problemas e reenvie o JSON completo dos "
                     "arquivos necessários.")
        return "\n".join(lines)

    @staticmethod
    def _count_files(project_dir: str) -> int:
        total = 0
        for _root, _dirs, files in os.walk(project_dir):
            total += len(files)
        return total

    def run_all(self) -> list[dict[str, Any]]:
        return [self.run_task(t) for t in self.tasks]
