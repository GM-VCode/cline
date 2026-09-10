# -*- coding: utf-8 -*-
"""Reproduz a escrita do ProxyRecorder no agent_runs (diagnóstico)."""
import sys
from typing import Any
sys.path.insert(0, ".")

from data.mongodb.store import TaskStore

store = TaskStore()
print("store.active:", store.active)
print("store.error:", store.error)

doc: dict[str, Any] = {
    "task_id": "diag-teste",
    "instruction": "teste de escrita",
    "status": "in_progress",
    "finished": False,
    "requests_count": 1,
    "last_seen_at": 1788904000.0,
    "error": "",
}
r = store.upsert_agent_run(doc, task_id="diag-teste")
print("upsert last_backend:", store.agent_runs.last_backend)
print("store.error depois:", store.error)
g = store.get_agent_run("diag-teste")
print("get_agent_run:", "OK" if g else "None")
