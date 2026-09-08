# ============================================================
#  tools/benchmarks/executor_llama.py — class LlamaExecutor
#  ModelExecutor REAL: chama o llama-server local via
#  /v1/chat/completions e aplica o código que o modelo genera.
#  Mide tool_calls (prompt de system que pede edição) e tokens.
# ============================================================

import os
import json
import urllib.request

from tools.benchmarks.runner import ModelExecutor
from app.agent.debug import get_agent_logger

DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"
SYSTEM = (
    "Você é um engenheiro de software cuidadoso. Dada uma tarefa que cria "
    "ou corrige código, responda EXCLUSIVAMENTE com um bloco JSON: "
    "{\"files\": {\"<relative_path>\": \"<conteúdo do arquivo>\"}, "
    "\"edits\": [{\"file\": \"<path>\", \"find\": \"<trecho exato e único>\", "
    "\"replace\": \"<substituição>\"}], "
    "\"run\": \"<comando opcional para você mesmo validar o resultado>\", "
    "\"note\": \"<breve resumo>\"} "
    "Para CRIAR arquivo, use 'files' (conteúdo completo). Para MODIFICAR "
    "arquivo existente, prefira 'edits': o 'find' deve ser um trecho que "
    "ocorre EXATAMENTE UMA vez no arquivo (copie-o fielmente, com "
    "indentação). Todos os campos são opcionais, exceto um deles. "
    "Se incluir \"run\", ele será executado no projeto e a saída te será "
    "devolvida se falhar — use para testar seu próprio código antes de "
    "declarar que terminou."
)


class LlamaExecutor(ModelExecutor):
    """Executor real via llama-server local."""

    def __init__(self, url: str = DEFAULT_URL, temperature: float = 0.2,
                 max_tokens: int = 2048, enable_thinking: bool = False,
                 retry_temperature: float = 0.7):
        self.url = url
        self.temperature = temperature
        self._defer_apply = False
        self.max_tokens = max_tokens
        self.enable_thinking = enable_thinking
        # temperatura maior no retry: prompt idêntico com temperature baixa
        # reproduz a mesma resposta (loop); subir quebra o determinismo.
        self.retry_temperature = retry_temperature
        self.last_raw: dict | None = None

    def _build_messages(self, instruction: str,
                        feedback: str | None = None) -> list:
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": instruction}]
        if feedback:
            messages.append({"role": "assistant",
                             "content": "Entendi, vou corrigir."})
            messages.append({"role": "user", "content": feedback})
        return messages

    def _request(self, instruction: str, project_dir: str,
                 feedback: str | None = None) -> dict:
        payload = {
            "model": "LunarIA",
            "messages": self._build_messages(instruction, feedback),
            "temperature": (self.retry_temperature if feedback
                            else self.temperature),
            "max_tokens": self.max_tokens,
            # Qwythos-9B: modelo de raciocínio; desliga o <think>...</think>
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
        }
        req = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))

    @staticmethod
    def _extract_content(resp: dict) -> str:
        try:
            content = resp["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError):
            return ""
        # robustez: se o modelo raciocinou, remove o bloco <think>...</think>
        if "<think>" in content:
            end = content.find("</think>")
            content = content[end + len("</think>"):] if end != -1 else content
        return content

    def _parse_files(self, content: str) -> tuple:
        """Extrai (files, edits, run_cmd, action) do JSON do modelo."""
        content = content.strip()
        # robustez: extraer el sub-bloco JSON de files si viene suelto
        start = content.find("{")
        end = content.rfind("}")
        if start == -1:
            return {}, [], None, None
        blob = content[start:end + 1] if end > start else content[start:]
        try:
            obj = json.loads(blob)
        except (ValueError, json.JSONDecodeError):
            obj = self._repair_json(blob)
        if not isinstance(obj, dict):
            return {}, [], None, None
        files = obj.get("files", {})
        if not isinstance(files, dict):
            files = {}
        edits = obj.get("edits", [])
        if not isinstance(edits, list):
            edits = []
        run_cmd = obj.get("run") or obj.get("cmd")
        action = obj.get("action")
        return (files, edits,
                run_cmd if isinstance(run_cmd, str) else None,
                action if isinstance(action, str) else None)

    @staticmethod
    def _repair_json(blob: str):
        """Tenta fechar JSON truncado (aspas/chaves/colchetes abertos)."""
        stack = []
        in_str = False
        esc = False
        for ch in blob:
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch in "{[":
                stack.append(ch)
            elif ch in "}]":
                if stack:
                    stack.pop()
        fixed = blob
        if esc:
            fixed += '"'
        if in_str:
            fixed += '"'
        for ch in reversed(stack):
            fixed += "}" if ch == "{" else "]"
        try:
            return json.loads(fixed)
        except (ValueError, json.JSONDecodeError):
            return None

    def _apply_files(self, files: dict, project_dir: str):
        for rel, body in files.items():
            path = os.path.join(project_dir, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(body)

    def execute(self, instruction: str, project_dir: str) -> dict:
        return self._run(instruction, project_dir)

    def execute_with_feedback(self, instruction: str, project_dir: str,
                              feedback: str) -> dict:
        return self._run(instruction, project_dir, feedback=feedback)

    def execute_action(self, instruction: str, project_dir: str,
                       history: list) -> dict:
        """11c: um passo por vez; histórico de observações no feedback.
        NÃO aplica nada — quem aplica é o ActionLoop (evita dupla aplicação)."""
        from app.agent.runner.actions import ACTION_SYSTEM
        parts = [ACTION_SYSTEM]
        for i, h in enumerate(history, 1):
            parts.append(f"passo {i} ({h['action']}):\n{h['observation'][:400]}")
        parts.append("Responda com o PRÓXIMO passo (um por vez).")
        fb = "\n\n".join(parts)
        self._defer_apply = True
        try:
            result = self._run(instruction, project_dir, feedback=fb)
        finally:
            self._defer_apply = False
        result.setdefault("action", None)
        return result

    def _run(self, instruction: str, project_dir: str,
             feedback: str | None = None) -> dict:
        log = get_agent_logger()
        if log:
            log.debug(
                f"REQUEST instr={len(instruction)}ch feedback={'sim' if feedback else 'nao'}")
        resp = self._request(instruction, project_dir, feedback=feedback)
        self.last_raw = resp
        content = self._extract_content(resp)
        files, edits, run_cmd, action = self._parse_files(content)
        edit_report = []
        if not self._defer_apply:
            self._apply_files(files, project_dir)
            if edits:
                from app.agent.apply import PatchApplier
                ok_edits, edit_report = PatchApplier().apply(project_dir,
                                                             edits)
                if not ok_edits:
                    # edit rejeitado: nada foi escrito; devolve como falha
                    return {
                        "tool_calls": 0, "retries": 0, "tokens": 0,
                        "files_written": [], "files": {},
                        "edits_failed": True,
                        "edit_errors": edit_report, "run": None,
                        "content_preview": content[:120],
                    }
        else:
            edit_report = [f"pendente: {len(edits)} edit(s)"]
        if log:
            log.debug(f"RAW_CONTENT ({len(content)}ch): {content[:1500]!r}")
            log.debug(f"FILES_PARSED: {sorted(files.keys())} "
                      f"EDITS: {len(edits)} RUN: {run_cmd!r}")

        usage = resp.get("usage", {})
        return {
            "tool_calls": len(files) + len(edits),
            "retries": 0,
            "tokens": (usage.get("total_tokens", 0)
                       if isinstance(usage, dict) else 0),
            "files_written": sorted(files.keys()),
            "files": files,
            "edits": edits,
            "edits_applied": edit_report,
            "run": run_cmd,
            "action": action,
            "content_preview": content[:120],
        }