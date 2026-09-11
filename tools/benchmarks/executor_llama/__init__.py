import json
import urllib.request
from typing import Any, cast

from app.agent.debug import get_agent_logger, get_executor_logger
from tools.benchmarks.runner import ModelExecutor
from tools.benchmarks.executor_llama.parser import ExecutorResponseParser

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
    "IMPORTANTE: no código Python, importe no topo TUDO que usar "
    "(ex.: import re, import unicodedata) — nunca use um módulo sem "
    "importá-lo, e confira a lógica antes de responder. "
    "Se incluir \"run\", ele será executado no projeto e a saída te será "
    "devolvida se falhar — use para testar seu próprio código antes de "
    "declarar que terminou."
)
JsonObject = dict[str, Any]


class LlamaExecutor(ModelExecutor):
    """Executor real via llama-server local."""

    def __init__(self, url: str = DEFAULT_URL, temperature: float = 0.2,
                 max_tokens: int = 2048, enable_thinking: bool = False,
                 retry_temperature: float = 0.7) -> None:
        self.url = url
        self.temperature = temperature
        self._defer_apply = False
        self.max_tokens = max_tokens
        self.enable_thinking = enable_thinking
        self.retry_temperature = retry_temperature
        self.last_raw: JsonObject | None = None
        #: histórico de TODAS as respostas brutas (1 por tentativa) —
        #: usado pelo _dump_debug do BenchmarkRunner p/ falhas visíveis
        self.raw_history: list[JsonObject] = []
        self.last_parsed: JsonObject | None = None
        self.parser = ExecutorResponseParser()

    def _build_messages(self, instruction: str, project_dir: str,
                        feedback: str | None = None) -> list[JsonObject]:
        # contexto do projeto: o modelo PRECISA ver o código que existe
        # (mesma visão do AgentRunner) — editar no chute era a causa de
        # respostas longas/erradas nas tarefas de editar/refatorar.
        conteudo = instruction
        try:
            from app.agent.context import ProjectContext
            conteudo = (instruction + "\n\n"
                        + ProjectContext(project_dir).to_prompt())
        except Exception:  # contexto é melhor-effort; nunca quebra o executor
            pass
        messages: list[JsonObject] = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": conteudo},
        ]
        if feedback:
            messages.extend([
                {"role": "assistant", "content": "Entendi, vou corrigir."},
                {"role": "user", "content": feedback},
            ])
        return messages

    def _request(self, instruction: str, project_dir: str,
                 feedback: str | None = None) -> JsonObject:
        payload: JsonObject = {
            "model": "LunarIA", "messages": self._build_messages(
                instruction, project_dir, feedback),
            "temperature": self.retry_temperature if feedback else self.temperature,
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"enable_thinking": self.enable_thinking},
        }
        request = urllib.request.Request(
            self.url, data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=120) as response:
            raw: object = json.loads(response.read().decode("utf-8"))
        return cast(JsonObject, raw) if isinstance(raw, dict) else {}

    def _parse_files(
        self,
        content: str,
    ) -> tuple[JsonObject, list[Any], str | None, str | None]:
        return self.parser.parse(content)

    def _apply_files(self, files: JsonObject, project_dir: str) -> None:
        self.parser.apply_files(files, project_dir)

    def execute(self, instruction: str, project_dir: str) -> JsonObject:
        return self._run(instruction, project_dir)

    def execute_with_feedback(self, instruction: str, project_dir: str,
                              feedback: str) -> JsonObject:
        return self._run(instruction, project_dir, feedback=feedback)

    def execute_action(self, prompt: str, project_dir: str,
                       history: list[dict[str, str]]) -> JsonObject:
        from app.agent.runner.actions import ACTION_SYSTEM
        parts = [ACTION_SYSTEM]
        parts.extend(f"passo {i} ({item['action']}):\n{item['observation'][:400]}"
                     for i, item in enumerate(history, 1))
        parts.append("Responda com o PRÓXIMO passo (um por vez).")
        self._defer_apply = True
        try:
            result = self._run(prompt, project_dir, feedback="\n\n".join(parts))
        finally:
            self._defer_apply = False
        result.setdefault("action", None)
        return result

    def _run(self, instruction: str, project_dir: str,
             feedback: str | None = None) -> JsonObject:
        log = get_agent_logger()
        if log:
            log.debug(f"REQUEST instr={len(instruction)}ch feedback={'sim' if feedback else 'nao'}")
        elog = get_executor_logger()
        if elog:
            elog.debug(f"EXECUTOR CALL instr={len(instruction)}ch "
                       f"feedback={'sim' if feedback else 'nao'} "
                       f"project_dir={project_dir}")
        response = self._request(instruction, project_dir, feedback=feedback)
        self.last_raw = response
        self.raw_history.append(response)
        if elog:
            raw = str(response)
            elog.debug(f"RESPONSE RAW ({len(raw)}ch): {raw[:2000]}")
        content = self.parser.extract_content(response)
        files, edits, run_cmd, action = self._parse_files(content)
        edit_report: list[Any] = []
        if not self._defer_apply:
            self._apply_files(files, project_dir)
            if edits:
                from app.agent.apply import PatchApplier
                ok, edit_report = PatchApplier().apply(project_dir, edits)
                if not ok:
                    result = {"tool_calls": 0, "retries": 0, "tokens": 0,
                              "files_written": [], "files": {}, "edits_failed": True,
                              "edit_errors": edit_report, "run": None,
                              "content_preview": content[:120]}
                    self.last_parsed = result
                    return result
        else:
            edit_report = [f"pendente: {len(edits)} edit(s)"]
        usage_value: object = response.get("usage", {})
        usage: JsonObject = (
            cast(JsonObject, usage_value)
            if isinstance(usage_value, dict)
            else {}
        )
        result = {
            "tool_calls": len(files) + len(edits), "retries": 0,
            "tokens": usage.get("total_tokens", 0),
            "files_written": sorted(files.keys()), "files": files, "edits": edits,
            "edits_applied": edit_report, "run": run_cmd, "action": action,
            "content_preview": content[:120],
        }
        self.last_parsed = result
        return result


__all__ = ["LlamaExecutor", "DEFAULT_URL", "SYSTEM"]
