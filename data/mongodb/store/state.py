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
        self.last_backend = None    # "mongo" | "json" no último save

    @property
    def _coll(self):
        """Coleção Mongo ativa (None se sem conexão ou Mongo off)."""
        if self.conn is not None and self.conn.active:
            return self.conn.collection("tasks")
        return None

    def save(self, payload: dict, task_id: str | None = None) -> dict:
        if not isinstance(payload, dict):
            payload = {}
        payload = dict(payload)
        tid = task_id or self.task_id
        payload.setdefault("task_id", tid)
        payload.setdefault("updated_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
        # o JSON é sempre um espelho; last_backend indica o primário
        self.last_backend = "json"
        coll = self._coll
        if coll is not None:
            try:
                coll.replace_one({"task_id": tid}, payload, upsert=True)
                self.last_backend = "mongo"
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (save_state): {exc}")
        JsonFile.write(self.state_path, payload)
        return payload

    def load(self, task_id: str | None = None) -> dict:
        tid = task_id or self.task_id
        coll = self._coll
        if coll is not None:
            try:
                doc = coll.find_one({"task_id": tid})
                if doc:
                    return {k: v for k, v in doc.items() if k != "_id"}
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (load_state): {exc}")
        data = JsonFile.read(self.state_path)
        if not isinstance(data, dict):
            return {}
        # no fallback JSON, só devolve se o id bater (arquivo é espelho único)
        return data if data.get("task_id", self.task_id) == tid else {}