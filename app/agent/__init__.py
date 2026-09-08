# ============================================================
#  app/agent/__init__.py — PACOTE app.agent (agente real)
#
#  Núcleo do agente reutilizável (fora do benchmark):
#    checks.py  -> class CheckRunner (comando de verificação)
#    runner.py  -> class AgentRunner (modelo + valida + retry)
#
#  API:  from app.agent import AgentRunner
# ============================================================

from app.agent.checks import CheckRunner      # noqa: F401
from app.agent.context import ProjectContext  # noqa: F401
from app.agent.identity import AgentIdentity  # noqa: F401
from app.agent.runner import AgentRunner      # noqa: F401

__all__ = ["AgentRunner", "CheckRunner", "ProjectContext", "AgentIdentity"]
