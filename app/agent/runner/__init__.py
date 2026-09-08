# ============================================================
#  app/agent/runner/ — pacote do núcleo do agente (ex-runner.py)
#  API pública intacta: from app.agent.runner import AgentRunner
# ============================================================

from app.agent.runner.core import AgentRunner  # noqa: F401

__all__ = ["AgentRunner"]
