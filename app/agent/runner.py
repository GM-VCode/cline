# ============================================================
#  app/agent/runner.py — class AgentRunner
#  Núcleo do agente REAL (fora do benchmark): instrução +
#  projeto + comando de verificação. Aplica os arquivos que o
#  modelo gerar, valida, e em caso de falha reenvia com o
#  feedback do erro (retry), até max_attempts.
# ============================================================

import os
import time

from app.agent.checks import CheckRunner
from app.agent.context import ProjectContext
from app.agent.debug import get_agent_logger


class AgentRunner:
    """Executa uma tarefa de código com o modelo + verificação real."""

    def __init__(self, executor, check_cmd: list = None, max_attempts: int = 2,
                 check_timeout: int = 120, use_context: bool = True,
                 identity=None, store=None):
        self.executor = executor
        self.check_cmd = check_cmd or []
        self.max_attempts = max(1, max_attempts)
        self.checks = CheckRunner(timeout=check_timeout)
        self.use_context = use_context
        self.identity = identity
        self.store = store  # TaskStore opcional: registra cada execução

    def _compose(self, instruction: str, project_dir: str) -> str:
        parts = []
        if self.identity:
            ident = self.identity.to_prompt()
            if ident:
                parts.append(ident)
        if self.use_context:
            parts.append(ProjectContext(project_dir).to_prompt())
        parts.append(f"INSTRUÇÃO: {instruction}")
        return "\n\n".join(parts)

    def run(self, instruction: str, project_dir: str) -> dict:
        """Ciclo completo + registro na memória (se store configurado)."""
        result = self._run_cycle(instruction, project_dir)
        self._record(instruction, project_dir, result)
        return result

    def _run_cycle(self, instruction: str, project_dir: str) -> dict:
        """Ciclo completo: modelo -> aplica -> verifica -> retry."""
        if not os.path.isdir(project_dir):
            return {"finished": False, "error": "projeto não existe",
                    "attempts": 0, "retries": 0}
        prompt = self._compose(instruction, project_dir)

        started = time.time()
        attempts, retries = 0, 0
        ok, output, files = False, "", []
        internal_runs = 0
        log = get_agent_logger()
        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt
            try:
                if attempt == 1:
                    response = self.executor.execute(prompt, project_dir)
                else:
                    prev_files = (response or {}).get("files", {})
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
            files = response.get("files_written", []) if response else []
            # 11b: edits rejeitados (find não bateu) → feedback direto
            if response and response.get("edits_failed"):
                ok = False
                output = ("Suas edições foram REJEITADAS e nada foi "
                          "modificado:\n"
                          + "\n".join(response.get("edit_errors", []))
                          + "\nCorrija o 'find' (copie o trecho fielmente, "
                          "com indentação) e reenvie.")
                if log:
                    log.debug(f"EDITS_REJEITADOS: {response.get('edit_errors')}")
                continue
            # 11a: o modelo pode pedir para validar o próprio resultado
            run_cmd = (response or {}).get("run") if response else None
            if run_cmd:
                internal_runs += 1
                if log:
                    log.debug(f"RUN interno: {run_cmd!r}")
                run_ok, run_out = self.checks.run_shell(run_cmd, project_dir)
                if not run_ok:
                    # falhou o próprio teste do modelo -> feedback direto
                    ok, output = False, (
                        f"O comando que você pediu para executar falhou:\n"
                        f"$ {run_cmd}\n{run_out[:1500]}")
                    continue
            ok, output = self._check(project_dir)
            if ok:
                break

        return {
            "finished": ok,
            "error": None if ok else output[:500],
            "attempts": attempts,
            "retries": retries,
            "internal_runs": internal_runs,
            "files_written": files,
            "check_output": output[:2000],
            "elapsed_s": round(time.time() - started, 2),
        }

    def _record(self, instruction: str, project_dir: str, result: dict):
        """Registra a execução na memória (Mongo/JSON), se store configurado."""
        if self.store is None:
            return
        try:
            self.store.append_agent_run({
                "instruction": instruction[:500],
                "project": project_dir,
                "finished": result.get("finished"),
                "attempts": result.get("attempts"),
                "retries": result.get("retries"),
                "internal_runs": result.get("internal_runs", 0),
                "files": result.get("files_written", []),
                "elapsed_s": result.get("elapsed_s"),
                "error": (result.get("error") or "")[:300],
            })
        except Exception as exc:  # memória nunca quebra o agente
            log = get_agent_logger()
            if log:
                log.warn(f"falha ao registrar execução: {exc}")

    def _check(self, project_dir: str) -> tuple:
        if not self.check_cmd:
            return True, "sem comando de verificação configurado"
        return self.checks.run(self.check_cmd, project_dir)
