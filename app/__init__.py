# ============================================================
#  app/__init__.py — PACOTE app (código do servidor + agente)
#
#  Expone uma API pública limpa das classes do projeto:
#    from app import Config, LlamaServer, TaskStore
#
#  Los servicios viven en app/services/ (server, task_store).
#  Se mantienen los imports internos compatibles via re-export.
# ============================================================

from project_path import Config  # noqa: F401
from app.services.server import LlamaServer  # noqa: F401
from data.mongodb.store import TaskStore  # noqa: F401

__all__ = ["Config", "LlamaServer", "TaskStore"]
