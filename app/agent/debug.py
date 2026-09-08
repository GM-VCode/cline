# ============================================================
#  app/agent/debug.py — logger dedicado do agente
#  Escreve em logs/agent.log com nível DEBUG sempre (independe
#  do LOG_LEVEL do .env): prompt, resposta bruta do modelo,
#  arquivos aplicados e feedback de retry.
# ============================================================

import os

try:
    from tools.logger import AppLogger
    from app.config import Config
except ImportError:  # pragma: no cover
    AppLogger = None
    Config = None


def get_agent_logger():
    """AppLogger dedicado (logs/agent.log, nível DEBUG)."""
    if AppLogger is None:
        return None
    path = (getattr(Config, "AGENT_LOG", None) if Config else None) or os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "logs", "agent.log")
    return AppLogger(name="agent", path=path, level="DEBUG")
