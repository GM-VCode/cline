# ============================================================
#  data/mongodb/store/state.py — class StateRepo
#  Estado da tarefa (save/load) com Mongo ativo e fallback
#  automático a JSON (data/json/task-state.json).
# ============================================================

import time
from collections.abc import Callable, Mapping
from typing import Any, cast

from pymongo.collection import Collection

from data.mongodb.connection import MongoConnection
from data.mongodb.store.json_file import JsonFile


Document = dict[str, Any]
ErrorSink = Callable[[str], None]


MongoCollection = Collection[Document]


def _ignore_error(message: str) -> None:
    _ = message


class StateRepo:
    """Guarda/recupera o estado da tarefa atual."""

    def __init__(
        self,
        conn: MongoConnection | None,
        state_path: str,
        task_id: str = "current",
        error_sink: ErrorSink | None = None,
    ) -> None:
        self.conn = conn
        self.state_path = state_path
        self.task_id = task_id
        self.error_sink: ErrorSink = error_sink or _ignore_error
        self.last_backend: str | None = None

    @property
    def _coll(self) -> MongoCollection | None:
        """Coleção Mongo ativa (None se sem conexão ou Mongo off)."""
        if self.conn is not None and self.conn.active:
            return self.conn.collection("tasks")
        return None

    def save(
        self,
        payload: Mapping[str, Any],
        task_id: str | None = None,
    ) -> Document:
        data: Document = dict(payload)
        tid = task_id or self.task_id
        data.setdefault("task_id", tid)
        data.setdefault("updated_at", time.strftime("%Y-%m-%dT%H:%M:%S"))
        # o JSON é sempre um espelho; last_backend indica o primário
        self.last_backend = "json"
        coll = self._coll
        if coll is not None:
            try:
                coll.replace_one({"task_id": tid}, data, upsert=True)
                self.last_backend = "mongo"
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (save_state): {exc}")
        JsonFile.write(self.state_path, data)
        return data

    def load(self, task_id: str | None = None) -> Document:
        tid = task_id or self.task_id
        coll = self._coll
        if coll is not None:
            try:
                doc = coll.find_one({"task_id": tid})
                if doc is not None:
                    return {
                        key: value
                        for key, value in doc.items()
                        if key != "_id"
                    }
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (load_state): {exc}")
        data = JsonFile.read(self.state_path)
        if not isinstance(data, dict):
            return {}
        # no fallback JSON, só devolve se o id bater (arquivo é espelho único)
        state: Document = cast(Document, data)
        return state if state.get("task_id", self.task_id) == tid else {}