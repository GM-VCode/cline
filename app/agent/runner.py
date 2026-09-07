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


class AgentRunner:
    """Executa uma tarefa de código com o modelo + verificação real."""

    def __init__(self, executor, check_cmd: list = None, max_attempts: int = 2,
                 check_timeout: int = 120):
        self.executor = executor
        self.check_cmd = check_cmd or []
        self.max_attempts = max(1, max_attempts)
        self.checks = CheckRunner(timeout=check_timeout)

    def run(self, instruction: str, project_dir: str) -> dict:
        """Ciclo completo: modelo -> aplica -> verifica -> retry."""
        if not os.path.isdir(project_dir):
            return {"finished": False, "error": "projeto não existe",
                    "attempts": 0, "retries": 0}

        started = time.time()
        attempts, retries = 0, 0
        ok, output, files = False, "", []
        for attempt in range(1, self.max_attempts + 1):
            attempts = attempt
            try:
                if attempt == 1:
                    response = self.executor.execute(instruction, project_dir)
                else:
                    feedback = CheckRunner.feedback_from(instruction, output)
                    response = self.executor.execute_with_feedback(
                        instruction, project_dir, feedback)
                    retries += 1
            except Exception as exc:
                return {"finished": False, "error": str(exc),
                        "attempts": attempts, "retries": retries,
                        "elapsed_s": round(time.time() - started, 2)}
            files = response.get("files_written", []) if response else []
            ok, output = self._check(project_dir)
            if ok:
                break

        return {
            "finished": ok,
            "error": None if ok else output[:500],
            "attempts": attempts,
            "retries": retries,
            "files_written": files,
            "check_output": output[:2000],
            "elapsed_s": round(time.time() - started, 2),
        }

    def _check(self, project_dir: str) -> tuple:
        if not self.check_cmd:
            return True, "sem comando de verificação configurado"
        return self.checks.run(self.check_cmd, project_dir)
