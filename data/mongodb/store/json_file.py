# ============================================================
#  data/mongodb/store/json_file.py — class JsonFile
#  Leitura/escrita JSON com tolerância a falhas (retorna None
#  em erro de leitura; nunca lança em escrita).
# ============================================================

import json
from typing import Any


class JsonFile:
    """Helpers de I/O JSON tolerantes a falhas.

    Nunca levanta: em falha, loga o motivo em logs/app/fallback.log
    (auditoria da memória) e retorna None/False.
    """

    @staticmethod
    def _log_failure(operacao: str, path: str, erro: Exception) -> None:
        """Registra a falha de I/O da memória (import lazy, nunca levanta)."""
        try:
            from app.agent.debug import get_fallback_logger
            log = get_fallback_logger()
            if log:
                log.error(f"JSON {operacao} falhou em {path}: {erro}")
        except Exception:  # pragma: no cover — logging nunca quebra o store
            pass

    @staticmethod
    def read(path: str) -> Any:
        """Lê JSON; None se arquivo não existe ou é inválido (loga o erro)."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            return None  # primeira leitura: ausente é estado normal
        except (OSError, ValueError) as exc:
            JsonFile._log_failure("read", path, exc)
            return None

    @staticmethod
    def write(path: str, data: Any) -> bool:
        """Escreve JSON; True em sucesso (nunca lança; loga a falha)."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except OSError as exc:
            JsonFile._log_failure("write", path, exc)
            return False