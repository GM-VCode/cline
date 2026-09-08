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
    "\"run\": \"<comando opcional para você mesmo validar o resultado>\", "
    "\"note\": \"<breve resumo>\"} "
    "Não escreva nada além do JSON. Cree só os arquivos necessários. "
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
        self.max_tokens = max_tokens
        self.enable_thinking = enable_thinking
        # temperatura maior no retry: prompt idêntico com temperature baixa
        # reproduz a mesma resposta (loop); subir quebra o determinismo.
        self.retry_temperature = retry_temperature
        self.last_raw = None

    def _build_messages(self, instruction: str,
                        feedback: str = None) -> list:
        messages = [{"role": "system", "content": SYSTEM},
                    {"role": "user", "content": instruction}]
        if feedback:
            messages.append({"role": "assistant",
                             "content": "Entendi, vou corrigir."})
            messages.append({"role": "user", "content": feedback})
        return messages

    def _request(self, instruction: str, project_dir: str,
                 feedback: str = None) -> dict:
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
        """Extrai (files, run_cmd) do JSON que o modelo devolve."""
        content = content.strip()
        # robustez: extraer el sub-bloco JSON de files si viene suelto
        try:
            start = content.find("{")
            end = content.rfind("}")
            obj = json.loads(content[start:end + 1])
        except (ValueError, json.JSONDecodeError):
            return {}, None
        files = obj.get("files", {})
        run_cmd = obj.get("run")
        if not isinstance(files, dict):
            files = {}
        return files, (run_cmd if isinstance(run_cmd, str) else None)

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

    def _run(self, instruction: str, project_dir: str,
             feedback: str = None) -> dict:
        log = get_agent_logger()
        if log:
            log.debug(
                f"REQUEST instr={len(instruction)}ch feedback={'sim' if feedback else 'nao'}")
        resp = self._request(instruction, project_dir, feedback=feedback)
        self.last_raw = resp
        content = self._extract_content(resp)
        files, run_cmd = self._parse_files(content)
        self._apply_files(files, project_dir)
        if log:
            log.debug(f"RAW_CONTENT ({len(content)}ch): {content[:1500]!r}")
            log.debug(f"FILES_PARSED: {sorted(files.keys())} RUN: {run_cmd!r}")

        usage = resp.get("usage", {})
        return {
            "tool_calls": len(files),        # nº de arquivos que "escreve"
            "retries": 0,
            "tokens": (usage.get("total_tokens", 0)
                       if isinstance(usage, dict) else 0),
            "files_written": sorted(files.keys()),
            "files": files,
            "run": run_cmd,
            "content_preview": content[:120],
        }