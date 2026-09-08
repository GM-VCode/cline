# ============================================================
#  app/services/proxy/__init__.py — API pública do proxy
#  Cline → ProxyServer(:8081) → llama-server(:8080), gravando
#  cada tarefa do Cline no Mongo (coleções tasks + agent_runs).
# ============================================================

from app.services.proxy.handler import ProxyHandler  # noqa: F401
from app.services.proxy.server import ProxyServer  # noqa: F401
from app.services.proxy.sessions import SessionRegistry  # noqa: F401

__all__ = ["ProxyHandler", "ProxyServer", "SessionRegistry"]
