# ============================================================
#  data/mongodb/store/history.py — class HistoryCollection
#  Histórico genérico (validações, diagnósticos...): append/list
#  com Mongo ativo e fallback automático a JSON. Reutilizável.
# ============================================================

import time

from data.mongodb.store.json_file import JsonFile


class HistoryCollection:
    """Append/list com Mongo (se ativo) e fallback a arquivo JSON."""

    def __init__(self, conn, coll_name: str, json_path: str, label: str,
                 task_id: str = "current", error_sink=None):
        self.conn = conn
        self.coll_name = coll_name
        self.json_path = json_path
        self.label = label          # p/ mensagens de erro
        self.task_id = task_id
        self.error_sink = error_sink or (lambda msg: None)
        self.last_backend = None    # "mongo" | "json" no último append

    @property
    def _coll(self):
        """Coleção Mongo ativa (None se sem conexão ou Mongo off)."""
        if self.conn is not None and self.conn.active:
            return self.conn.collection(self.coll_name)
        return None

    def append(self, entry: dict, task_id: str | None = None) -> dict:
        if not isinstance(entry, dict):
            entry = {"value": entry}
        entry = dict(entry)
        entry.setdefault("task_id", task_id or self.task_id)
        entry.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        coll = self._coll
        if coll is not None:
            try:
                coll.insert_one(dict(entry))
                self.last_backend = "mongo"
                return entry
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo ({self.coll_name}): {exc}")
        return self._append_json(entry)

    def list(self, limit: int = 20, task_id: str | None = None) -> list:
        tid = task_id or self.task_id
        coll = self._coll
        if coll is not None:
            try:
                cursor = (coll.find({"task_id": tid})
                          .sort("_id", -1).limit(limit))
                out = [{k: v for k, v in doc.items() if k != "_id"}
                       for doc in cursor]
                return out
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (list {self.coll_name}): {exc}")
        history = JsonFile.read(self.json_path)
        if not isinstance(history, list):
            return []
        # fallback JSON é um arquivo único: filtra pelo task_id
        history = [e for e in history
                   if isinstance(e, dict)
                   and e.get("task_id") == tid]
        return list(reversed(history[-limit:]))

    def _append_json(self, entry: dict) -> dict:
        history = JsonFile.read(self.json_path)
        if not isinstance(history, list):
            history = []
        history.append(entry)
        JsonFile.write(self.json_path, history)
        self.last_backend = "json"
        return entry