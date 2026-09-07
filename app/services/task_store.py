# ============================================================
#  app/services/task_store.py — RE-EXPORTE de TaskStore
#  La clase real vive en data/mongodb/store.py (capa de datos).
#  Este archivo fino mantiene la API pública compatible:
#      from app import TaskStore
#      from app.task_store import TaskStore
# ============================================================

from data.mongodb.store import TaskStore  # noqa: F401

__all__ = ["TaskStore"]
