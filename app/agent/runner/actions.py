# ============================================================
#  app/agent/runner/actions.py — class ActionLoop
#  Etapa 11c: protocolo iterativo. O modelo responde UM passo
#  por vez: {"action": "write|edit|run|done", ...} e recebe a
#  observação do passo anterior. Orçamento duro (max_actions)
#  impede loops infinitos.
# ============================================================

import time

from app.agent.apply import PatchApplier
from app.agent.debug import get_agent_logger

ACTION_SYSTEM = (
    "Protocolo de ações: responda com UM passo por vez, em JSON: "
    "{\"action\": \"write\"|\"edit\"|\"run\"|\"done\", "
    "\"files\": {\"path\": \"conteúdo\"}, "
    "\"edits\": [{\"file\", \"find\", \"replace\"}], "
    "\"cmd\": \"<comando>\", \"note\": \"<resumo>\"}. "
    "write: cria arquivos. edit: modifica trecho único existente. "
    "run: executa um comando e recebe a saída. done: declare pronto "
    "quando estiver confiante (a verificação final ainda roda). "
    "Use 'run' para testar antes do done."
)

VALID_ACTIONS = ("write", "edit", "run", "done")


class ActionLoop:
    """Loop ação → observação → próxima ação, com orçamento de passos."""

    def __init__(self, executor, checks, project_dir: str,
                 check_cmd: list = None, max_actions: int = 8):
        self.executor = executor
        self.checks = checks
        self.project_dir = project_dir
        self.check_cmd = check_cmd or []
        self.max_actions = max(1, max_actions)
        self.history = []      # [{"action":..., "observation":...}]
        self.actions_used = 0
        self.files_written = []
        self.applier = PatchApplier()

    def _feedback(self, extra: str = None) -> str:
        parts = []
        for i, h in enumerate(self.history, 1):
            parts.append(f"passo {i} ({h['action']}): {h['observation'][:300]}")
        if extra:
            parts.append(extra)
        parts.append("Responda com o PRÓXIMO passo (um por vez).")
        return "\n".join(parts)

    def run(self, prompt: str) -> dict:
        """Executa o loop. Retorna o resultado final padrão do runner."""
        log = get_agent_logger()
        started = time.time()
        ok, output = False, ""
        invalid_streak = 0
        response = self.executor.execute_action(prompt, self.project_dir, [])
        while True:
            if response is None:
                ok, output = False, "executor não retornou resposta"
                break
            action = (response.get("action") or "").lower()
            if action not in VALID_ACTIONS:
                invalid_streak += 1
                self.actions_used += 1  # conta no orçamento (anti-loop)
                output = (f"Ação inválida: {action!r}. "
                          f"Use write|edit|run|done.")
                if invalid_streak >= 3:
                    ok = False
                    if log:
                        log.debug("ACOES_INVALIDAS_SEGUIDAS: abortando")
                    break
            elif action == "done":
                ok, output = True, (response.get("note") or "")[:300]
                break
            elif self.actions_used >= self.max_actions:
                ok = False
                output = (f"Orçamento de ações esgotado "
                          f"({self.max_actions}). Declare done ou "
                          f"resuma o essencial.")
                if log:
                    log.debug(f"ORCAMENTO_ESTOURADO: {self.actions_used}")
                break
            else:
                invalid_streak = 0
                self.actions_used += 1
                ok, output = self._do(action, response)
            observation = output if not ok else (
                output or "ação aplicada com sucesso")
            self.history.append(
                {"action": action, "observation": observation})
            if log:
                log.debug(f"ACAO {action}: ok={ok} "
                          f"obs={observation[:200]!r}")
            if not ok and action == "run" and "erro ao executar" not in output:
                pass  # falha de comando é observação, não aborta o loop
            response = self.executor.execute_action(
                prompt, self.project_dir, self.history)
        # a palavra final é a verificação oficial, não o 'done'
        if ok and self.check_cmd:
            ok, output = self.checks.run(self.check_cmd, self.project_dir)
        elif ok:
            output = output or "sem comando de verificação configurado"
        return {
            "finished": ok,
            "error": None if ok else output[:500],
            "attempts": 1,
            "retries": 0,
            "internal_runs": sum(
                1 for h in self.history if h["action"] == "run"),
            "actions_used": self.actions_used,
            "files_written": self.files_written,
            "check_output": output[:2000],
            "elapsed_s": round(time.time() - started, 2),
        }

    def _do(self, action: str, response: dict) -> tuple:
        """Executa a ação; retorna (ok, observation)."""
        if action == "write":
            files = response.get("files") or {}
            if not isinstance(files, dict) or not files:
                return False, "write sem 'files' válido"
            self._write_files(files)
            return True, f"escrito: {sorted(files.keys())}"
        if action == "edit":
            edits = response.get("edits") or []
            # tolerância: campos diretos na ação (file/find/replace no topo)
            if not edits and response.get("find") is not None:
                edits = [{"file": response.get("file"),
                          "find": response.get("find"),
                          "replace": response.get("replace")}]
            if not isinstance(edits, list) or not edits:
                return False, ("edit sem 'edits' válido — nada foi "
                               "modificado. Formato: {\"action\": \"edit\", "
                               "\"edits\": [{\"file\", \"find\", \"replace\"}]}")
            ok, report = self.applier.apply(self.project_dir, edits)
            return (ok, "; ".join(report) if ok
                    else "EDITS REJEITADOS (nada modificado): "
                         + "; ".join(report))
        if action == "run":
            cmd = response.get("cmd") or response.get("run")
            if not cmd:
                return False, "run sem 'cmd'"
            ok, out = self.checks.run_shell(cmd, self.project_dir)
            return ok, (f"$ {cmd}\n{out[:800]}" if out
                        else f"$ {cmd} (sem saída)")
        return False, f"ação não implementada: {action}"

    def _write_files(self, files: dict):
        import os
        base = os.path.abspath(self.project_dir)
        for rel, content in files.items():
            path = os.path.abspath(os.path.join(base, rel))
            if not path.startswith(base):
                continue
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
            self.files_written.append(rel)
