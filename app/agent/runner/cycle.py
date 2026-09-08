# ============================================================
#  app/agent/runner/cycle.py — class AttemptCycle
#  Uma rodada completa do protocolo antigo (11a/11b): recebe a
#  resposta do executor, aplica, roda o "run" interno e devolve
#  o desfecho (ok / feedback). Puro e sem I/O de memória.
# ============================================================

from app.agent.checks import CheckRunner
from app.agent.debug import get_agent_logger


class AttemptCycle:
    """Interpreta UMA resposta do executor e decide o desfecho."""

    def __init__(self, checks: CheckRunner, project_dir: str,
                 check_cmd: list = None):
        self.checks = checks
        self.project_dir = project_dir
        self.check_cmd = check_cmd or []
        self.internal_runs = 0

    def settle(self, response: dict) -> tuple:
        """Retorna (ok: bool, output: str).

        - ok=True  → verificação passou (ou run interno passou antes)
        - ok=False → 'output' é o feedback para o próximo retry
        """
        log = get_agent_logger()
        if response and response.get("edits_failed"):
            out = ("Suas edições foram REJEITADAS e nada foi modificado:\n"
                   + "\n".join(response.get("edit_errors", []))
                   + "\nCorrija o 'find' (copie o trecho fielmente, "
                     "com indentação) e reenvie.")
            if log:
                log.debug(f"EDITS_REJEITADOS: {response.get('edit_errors')}")
            return False, out
        run_cmd = (response or {}).get("run") if response else None
        if run_cmd:
            self.internal_runs += 1
            if log:
                log.debug(f"RUN interno: {run_cmd!r}")
            run_ok, run_out = self.checks.run_shell(run_cmd, self.project_dir)
            if not run_ok:
                return False, (f"O comando que você pediu para executar "
                               f"falhou:\n$ {run_cmd}\n{run_out[:1500]}")
        if not self.check_cmd:
            return True, "sem comando de verificação configurado"
        return self.checks.run(self.check_cmd, self.project_dir)
