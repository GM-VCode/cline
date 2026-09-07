# ============================================================
#  data/mongodb/store/state.py — class StateRepo
#  Estado da tarefa (save/load) com Mongo ativo e fallback
#  automático a JSON (data/json/task-state.json).
# ============================================================

import time

from data.mongodb.store.json_file import JsonFile


class StateRepo:
    """Guarda/recupera o estado da tarefa atual."""

    def __init__(self, conn, state_path: str, task_id: str = "current",
                 error_sink=None):
        self.conn = conn
        self.state_path = state_path
        self.task_id = task_id
        self.error_sink = error_sink or (lambda msg: None)

    @property
    def _coll(self):
        return self.conn.collection("tasks") if self.conn else None

    def save(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            payload = {}
        payload = dict(payload)
        payload.setdefault("task_id", self.task_id)
        payload.setdefault("updated_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if self.conn and self.conn.active:
            try:
                self._coll.replace_one({"task_id": self.task_id},
                                       payload, upsert=True)
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (save_state): {exc}")
        JsonFile.write(self.state_path, payload)
        return payload

    def load(self) -> dict:
        if self.conn and self.conn.active:
            try:
                doc = self._coll.find_one({"task_id": self.task_id})
                if doc:
                    return {k: v for k, v in doc.items() if k != "_id"}
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (load_state): {exc}")
        data = JsonFile.read(self.state_path)
        return data if isinstance(data, dict) else {}