# ============================================================
#  app/agent/runner/core.py — class AgentRunner
#  Fachada pública: orquestra composição do prompt, ciclos de
#  tentativa e registro na memória. A lógica de UMA resposta
#  vive em AttemptCycle (cycle.py); o prompt em PromptComposer.
# ============================================================

import os
import time
from typing import TYPE_CHECKING, Any, Protocol, cast

from app.agent.checks import CheckRunner
from app.agent.debug import get_agent_logger
from app.agent.runner.compose import PromptComposer
from app.agent.runner.cycle import AttemptCycle

if TYPE_CHECKING:  # só p/ anotações (evita import circular em runtime)
    from app.agent import AgentIdentity


class TaskStoreProtocol(Protocol):
    """Interface mínima de memória que o AgentRunner utiliza.

    Apenas save_state: agent_runs é gerenciado SOMENTE pelo proxy
    (ProxyRecorder) — o runner grava apenas o estado da tarefa.
    """

    def save_state(self, payload: dict[str, Any],
                   task_id: str | None = None) -> dict[str, Any]: ...


class ExecutorProtocol(Protocol):
    def execute(self, instruction: str, /,
                project_dir: str) -> dict[str, Any]: ...

    def execute_with_feedback(
        self,
        instruction: str,
        /,
        project_dir: str,
        feedback: str,
    ) -> dict[str, Any]: ...

    def execute_action(
        self,
        prompt: str,
        project_dir: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any] | None: ...


class AgentRunner:
    """Executa uma tarefa de código com o modelo + verificação real."""

    def __init__(self, executor: ExecutorProtocol,
                 check_cmd: list[str] | None = None,
                 max_attempts: int = 2, check_timeout: int = 120,
                 use_context: bool = True,
                 identity: "AgentIdentity | None" = None,
                 store: TaskStoreProtocol | None = None,
                 max_actions: int | None = None):
        self.executor = executor
        self.check_cmd = check_cmd or []
        self.max_attempts = max(1, max_attempts)
        self.checks = CheckRunner(timeout=check_timeout)
        self.composer = PromptComposer(use_context=use_context,
                                       identity=identity)
        self.store = store  # TaskStore opcional: registra cada execução
        self.max_actions = max_actions  # 11c: ativa o modo iterativo

    def run(self, instruction: str, project_dir: str) -> dict[str, Any]:
        """Ciclo completo + registro na memória (se store configurado)."""
        result = self._run_cycle(instruction, project_dir)
        self._record(instruction, project_dir, result)
        return result

    def _run_cycle(self, instruction: str, project_dir: str) -> dict[str, Any]:
        """Ciclo: modelo -> aplica -> verifica -> retry (até max_attempts)."""
        if not os.path.isdir(project_dir):
            return {"finished": False, "error": "projeto não existe",
                    "attempts": 0, "retries": 0}
        prompt = self.composer.compose(instruction, project_dir)

        # 11c: modo iterativo (ação → observação) quando max_actions é dado
        if self.max_actions is not None:
            from app.agent.runner.actions import ActionLoop
            loop = ActionLoop(self.executor, self.checks, project_dir,
                              check_cmd=self.check_cmd,
                              max_actions=self.max_actions)
            result = loop.run(prompt)
            result["elapsed_s"] = result.get("elapsed_s", 0)
            return result

        started = time.time()
        attempts, retries = 0, 0
        ok, output, files = False, "", []
        response: dict[str, Any] | None = None
        log = get_agent_logger()
        cycle = AttemptCycle(self.checks, project_dir, self.check_cmd)
        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt
            try:
                if attempt == 1:
                    response = self.executor.execute(prompt, project_dir)
                else:
                    files_value = (response or {}).get("files", {})
                    prev_files = (
                        cast(dict[str, str], files_value)
                        if isinstance(files_value, dict)
                        else {}
                    )
                    feedback = CheckRunner.feedback_from(
                        instruction, output, prev_files=prev_files)
                    if log:
                        log.debug(f"RETRY {attempt}: feedback={feedback[:400]!r}")
                    response = self.executor.execute_with_feedback(
                        prompt, project_dir, feedback)
                    retries += 1
            except Exception as exc:
                return {"finished": False, "error": str(exc),
                        "attempts": attempts, "retries": retries,
                        "elapsed_s": round(time.time() - started, 2)}
            files_value: object = (
                response.get("files_written", []) if response else []
            )
            files = (
                cast(list[str], files_value)
                if isinstance(files_value, list)
                else []
            )
            ok, output = cycle.settle(response)
            if ok:
                break

        return {
            "finished": ok,
            "error": None if ok else output[:500],
            "attempts": attempts,
            "retries": retries,
            "internal_runs": cycle.internal_runs,
            "files_written": files,
            "check_output": output[:2000],
            "elapsed_s": round(time.time() - started, 2),
        }

    def _record(self, instruction: str, project_dir: str,
                result: dict[str, Any]) -> None:
        """Registra o estado da tarefa (coleção tasks + data/json/task-state.json).

        NOTA: agent_runs é gerenciado SOMENTE pelo proxy (ProxyRecorder).
        O AgentRunner não escreve em agent_runs — só reporta o resultado via
        save_state, que é a coleção de estado da tarefa.
        """
        if self.store is None:
            return
        try:
            self.store.save_state({
                "objective": instruction[:500],
                "project": project_dir,
                "status": "completed" if result.get("finished")
                          else "failed",
                "last_result": {
                    "finished": result.get("finished"),
                    "attempts": result.get("attempts"),
                    "retries": result.get("retries"),
                    "actions_used": result.get("actions_used"),
                    "files": result.get("files_written", []),
                    "elapsed_s": result.get("elapsed_s"),
                    "error": (result.get("error") or "")[:300],
                },
            })
            log = get_agent_logger()
            if log:
                log.info(
                    "memória OK: tasks->{} (task_id={}, db={})"
                    .format(
                        getattr(getattr(self.store, "state", None),
                                "last_backend", "?"),
                        getattr(self.store, "task_id", "?"),
                        getattr(self.store, "db_name", "?"),
                    ))
        except Exception as exc:  # memória nunca quebra o agente
            log = get_agent_logger()
            if log:
                log.warn(f"falha ao registrar execução: {exc}")
