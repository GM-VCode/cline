# ============================================================
#  data/mongodb/store/json_file.py — class JsonFile
#  Leitura/escrita JSON com tolerância a falhas (retorna None
#  em erro de leitura; nunca lança em escrita).
# ============================================================

import json
from typing import Any


class JsonFile:
    """Helpers de I/O JSON tolerantes a falhas."""

    @staticmethod
    def read(path: str) -> Any:
        """Lê JSON; None se arquivo não existe ou é inválido."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    @staticmethod
    def write(path: str, data: Any) -> bool:
        """Escreve JSON; True em sucesso (nunca lança)."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except OSError:
            return False