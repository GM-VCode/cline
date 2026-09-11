# ============================================================
#  app/agent/identity.py — class AgentIdentity
#  Carrega app/agent/identity.md (quem é o agente, regras de
#  comportamento) e fornece o texto para o system prompt.
# ============================================================
import logging
import os

class AgentIdentity:

    """Identidade/regras do agente em arquivo editável (identity.md)."""

    def __init__(self, path: str | None = None):
        self._log = logging.getLogger(__name__)

        self.path = path or os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "identity.md"
        )

        self.text = self._load()

        self._log.info(
            f"identity: carregado de {self.path} "
            f"({len(self.text)} chars)"
        )

    def _load(self) -> str:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return f.read()

        except OSError as exc:
            self._log.warning(
                f"identity: ARQUIVO AUSENTE/ILEGÍVEL ({self.path}): {exc} "
                "— agente vai rodar sem identidade"
            )

            return ""

    def to_prompt(self) -> str:
        return self.text.strip()