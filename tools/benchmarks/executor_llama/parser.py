import json
import os
from typing import Any, cast


JsonObject = dict[str, Any]


class ExecutorResponseParser:
    """Extrai arquivos, patches, comandos e ações da resposta do modelo.

    Falhas de parse nunca levantam — mas cada uma fica registrada em
    logs/model/executor.log (get_executor_logger) para auditoria.
    """

    @staticmethod
    def _log(operacao: str, detalhe: str, level: str = "WARN") -> None:
        """Loga evento do parser; import lazy, nunca levanta."""
        try:
            from app.agent.debug import get_executor_logger
            log = get_executor_logger()
            if log:
                log.log(level, f"parser {operacao}: {detalhe}")
        except Exception:  # pragma: no cover — logging nunca quebra o parser
            pass

    def parse(
        self,
        content: str,
    ) -> tuple[JsonObject, list[Any], str | None, str | None]:
        content = content.strip()
        start, end = content.find("{"), content.rfind("}")
        if start == -1:
            self._log("sem-json", f"resposta sem '{{' "
                                  f"(primeiros 200ch: {content[:200]!r})")
            return {}, [], None, None
        blob = content[start:end + 1] if end > start else content[start:]
        try:
            raw: object = json.loads(blob)
        except (ValueError, json.JSONDecodeError):
            raw = self.repair(blob)
            if raw is None:
                self._log("json-invalido",
                          f"json.loads e repair falharam "
                          f"(blob {len(blob)}ch: {blob[:200]!r})", "ERROR")
        if not isinstance(raw, dict):
            self._log("nao-dict", f"JSON extraído não é objeto "
                                  f"({type(raw).__name__})", "ERROR")
            return {}, [], None, None
        obj: JsonObject = cast(JsonObject, raw)

        files_value: object = obj.get("files", {})
        edits_value: object = obj.get("edits", [])
        run_value: object = obj.get("run") or obj.get("cmd")
        action_value: object = obj.get("action")

        files: JsonObject = (
            cast(JsonObject, files_value)
            if isinstance(files_value, dict)
            else {}
        )
        edits: list[Any] = (
            cast(list[Any], edits_value)
            if isinstance(edits_value, list)
            else []
        )
        run = run_value if isinstance(run_value, str) else None
        action = action_value if isinstance(action_value, str) else None
        return files, edits, run, action

    @staticmethod
    def repair(blob: str) -> JsonObject | None:
        stack: list[str] = []
        in_string = False
        escaped = False
        for char in blob:
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
                continue
            if char == '"':
                in_string = True
            elif char in "{[":
                stack.append(char)
            elif char in "}]" and stack:
                stack.pop()
        fixed = blob + ('"' if escaped or in_string else '')
        for char in reversed(stack):
            fixed += "}" if char == "{" else "]"
        try:
            repaired: object = json.loads(fixed)
            return cast(JsonObject, repaired) if isinstance(repaired, dict) else None
        except (ValueError, json.JSONDecodeError):
            return None

    @staticmethod
    def extract_content(response: JsonObject) -> str:
        try:
            content = response["choices"][0]["message"]["content"] or ""
        except (KeyError, IndexError) as exc:
            ExecutorResponseParser._log(
                "sem-conteudo",
                f"resposta sem choices[0].message.content: {exc}", "ERROR")
            return ""
        if "<think>" in content:
            end = content.find("</think>")
            content = content[end + len("</think>"):] if end != -1 else content
        return content

    @staticmethod
    def apply_files(files: dict[str, str], project_dir: str) -> None:
        for relative, body in files.items():
            path = os.path.join(project_dir, relative)
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as stream:
                    stream.write(body)
            except OSError as exc:
                ExecutorResponseParser._log(
                    "apply", f"falha ao gravar {path}: {exc}", "ERROR")
                raise
