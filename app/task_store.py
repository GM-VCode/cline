# ============================================================
#  app/task_store.py — RE-EXPORTE de TaskStore (compatibilidade)
#  La clase vive en app/services/task_store.py (que apunta a
#  data/mongodb/store.py). Este archivo fino mantiene el import
#  antiguo:    from app.task_store import TaskStore
# ============================================================

from app.services.task_store import TaskStore  # noqa: F401

__all__ = ["TaskStore"]