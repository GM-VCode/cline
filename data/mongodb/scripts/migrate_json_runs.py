# -*- coding: utf-8 -*-
"""Migra os agent_runs do fallback JSON para o MongoDB (idempotente)."""
import json
import sys
sys.path.insert(0, ".")

from data.mongodb.store import TaskStore

store = TaskStore()
with open("data/json/agent_runs.json", encoding="utf-8") as fh:
    docs = json.load(fh)
n = 0
for d in docs:
    tid = d.get("task_id")
    if not tid:
        continue
    store.upsert_agent_run(d, task_id=tid)
    n += 1
print("migrados:", n, "| backend:", store.agent_runs.last_backend)
store.close()
