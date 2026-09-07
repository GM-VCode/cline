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

DEFAULT_URL = "http://127.0.0.1:8080/v1/chat/completions"
SYSTEM = (
    "Você é um engenheiro de software cuidadoso. Dada uma tarefa que cria "
    "código, responda EXCLUSIVAMENTE com um bloco JSON: "
    "{\"files\": {\"<relative_path>\": \"<contenido do arquivo>\"}, "
    "\"note\": \"<breve resumen>\"} "
    "Não escreva nada além do JSON. Cree só os arquivos necessários."
)


class LlamaExecutor(ModelExecutor):
    """Executor real via llama-server local."""

    def __init__(self, url: str = DEFAULT_URL, temperature: float = 0.2,
                 max_tokens: int = 2048, enable_thinking: bool = False):
        self.url = url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.enable_thinking = enable_thinking
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
            "temperature": self.temperature,
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

    def _parse_files(self, content: str) -> dict:
        """Extrai {\"files\": {...}} do JSON que o modelo devolve."""
        content = content.strip()
        # robustez: extraer el sub-bloco JSON de files si viene suelto
        try:
            start = content.find("{")
            end = content.rfind("}")
            obj = json.loads(content[start:end + 1])
        except (ValueError, json.JSONDecodeError):
            return {}
        files = obj.get("files", {})
        return files if isinstance(files, dict) else {}

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
        resp = self._request(instruction, project_dir, feedback=feedback)
        self.last_raw = resp
        content = self._extract_content(resp)
        files = self._parse_files(content)
        self._apply_files(files, project_dir)

        usage = resp.get("usage", {})
        return {
            "tool_calls": len(files),        # nº de arquivos que "escreve"
            "retries": 0,
            "tokens": (usage.get("total_tokens", 0)
                       if isinstance(usage, dict) else 0),
            "files_written": sorted(files.keys()),
            "content_preview": content[:120],
        }