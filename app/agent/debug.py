# ============================================================
#  app/agent/debug.py — logger dedicado do agente
#  Escreve em logs/agent.log com nível DEBUG sempre (independe
#  do LOG_LEVEL do .env): prompt, resposta bruta do modelo,
#  arquivos aplicados e feedback de retry.
# ============================================================

import os

from project_path import Config
from tools.logger import AppLogger


def get_agent_logger() -> AppLogger:
    """AppLogger dedicado (logs/agent.log, nível DEBUG).

    Override de path via env AGENT_LOG_PATH (usado pelos tests
    para não poluírem o log real).
    """
    path = os.environ.get("AGENT_LOG_PATH") or Config().AGENT_LOG
    return AppLogger(name="agent", path=path, level="DEBUG")
