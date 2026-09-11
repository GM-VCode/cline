# ============================================================
#  data/mongodb/store/history.py — class HistoryCollection
#  Histórico genérico (validações, diagnósticos...): append/list
#  com Mongo ativo e fallback automático a JSON. Reutilizável.
# ============================================================

import time
from collections.abc import Callable, Iterable
from typing import Any, cast

from pymongo.collection import Collection

from data.mongodb.connection import MongoConnection
from data.mongodb.store.json_file import JsonFile

Document = dict[str, Any]


MongoCollection = Collection[Document]


def _ignore_error(_message: str) -> None:
    pass


class HistoryCollection:
    """Append/list com Mongo (se ativo) e fallback a arquivo JSON."""

    def __init__(self, conn: MongoConnection | None, coll_name: str,
                 json_path: str, label: str, task_id: str = "current",
                 error_sink: Callable[[str], None] | None = None) -> None:
        self.conn = conn
        self.coll_name = coll_name
        self.json_path = json_path
        self.label = label          # p/ mensagens de erro
        self.task_id = task_id
        self.error_sink: Callable[[str], None] = error_sink or _ignore_error
        self.last_backend: str | None = None

    @property
    def _coll(self) -> MongoCollection | None:
        """Coleção Mongo ativa (None se sem conexão ou Mongo off)."""
        if self.conn is not None and self.conn.active:
            return self.conn.collection(self.coll_name)
        return None

    @staticmethod
    def _document(value: object) -> Document:
        if isinstance(value, dict):
            return cast(Document, value)
        return {"value": value}

    @staticmethod
    def _history(value: object) -> list[Document]:
        if not isinstance(value, list):
            return []
        items: list[Any] = cast(list[Any], value)
        return [cast(Document, item) for item in items if isinstance(item, dict)]

    def append(self, entry: object, task_id: str | None = None) -> Document:
        document = self._document(entry)
        document.setdefault("task_id", task_id or self.task_id)
        document.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        coll = self._coll
        if coll is not None:
            try:
                coll.insert_one(document)
                self.last_backend = "mongo"
                return document
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo ({self.coll_name}): {exc}")
        return self._append_json(document)

    def upsert(self, entry: object, task_id: str | None = None,
               event: Document | None = None) -> Document:
        """Atualiza o registro existente da conversa ou cria se não existir.

        Mantém exatamente 1 documento por task_id (não acumula duplicatas):
        se o registro já existiu, os campos de ``entry`` sobrescrevem os
        antigos e ``ts``/``last_update`` refletem o request mais recente.
        ``event`` (opcional) é anexado à timeline (event sourcing).
        """
        document = self._document(entry)
        tid = task_id or self.task_id
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        document.setdefault("task_id", tid)
        document.setdefault("ts", now)
        coll = self._coll
        if coll is not None:
            try:
                sets = dict(document)
                sets["last_update"] = now
                # created_at vem do doc base; nunca pode estar em $set E
                # $setOnInsert ao mesmo tempo (conflito no MongoDB).
                created = sets.pop("created_at", now)
                update: Document = {"$set": sets,
                                    "$setOnInsert": {"created_at": created}}
                if event is not None:
                    update["$push"] = {"timeline": event}
                coll.update_one({"task_id": tid}, update, upsert=True)
                self.last_backend = "mongo"
                return sets
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (upsert {self.coll_name}): {exc}")
        return self._upsert_json(document, tid, event)

    def _upsert_json(self, entry: Document, tid: str,
                     event: Document | None = None) -> Document:
        history = self._history(JsonFile.read(self.json_path))
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for i, old in enumerate(history):
            if old.get("task_id") == tid:
                merged = dict(old)
                merged.update(entry)
                if event is not None:
                    value = merged.get("timeline")
                    timeline: list[Document] = (
                        cast(list[Document], value)
                        if isinstance(value, list)
                        else []
                    )
                    timeline.append(event)
                    merged["timeline"] = timeline
                merged["last_update"] = now
                history[i] = merged
                entry = merged
                break
        else:
            if event is not None:
                entry = dict(entry)
                entry["timeline"] = [event]
            history.append(entry)
        JsonFile.write(self.json_path, history)
        self.last_backend = "json"
        return entry

    def get_one(self, task_id: str | None = None) -> Document | None:
        """Documento único da conversa (None se ainda não existe)."""
        tid = task_id or self.task_id
        coll = self._coll
        if coll is not None:
            try:
                doc = coll.find_one({"task_id": tid})
                if doc is None:
                    return None
                return {
                    k: v for k, v in doc.items() if k != "_id"
                }
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (get_one {self.coll_name}): {exc}")
        history = self._history(JsonFile.read(self.json_path))
        for e in reversed(history):
            if e.get("task_id") == tid:
                return e
        return None

    def list(self, limit: int = 20, task_id: str | None = None) -> list[Document]:
        tid = task_id or self.task_id
        coll = self._coll
        if coll is not None:
            try:
                filtro: dict[str, Any] = ({} if tid == "*"
                                          else {"task_id": tid})
                cursor: Iterable[Document] = (coll.find(filtro)
                                              .sort("_id", -1).limit(limit))
                out: list[Document] = [{k: v for k, v in doc.items() if k != "_id"}
                                       for doc in cursor]
                return out
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (list {self.coll_name}): {exc}")
        history = self._history(JsonFile.read(self.json_path))
        # fallback JSON é um arquivo único: filtra pelo task_id
        # ("*" = lista tudo, sem filtrar)
        if tid != "*":
            history = [e for e in history if e.get("task_id") == tid]
        return list(reversed(history[-limit:]))

    def _append_json(self, entry: Document) -> Document:
        history = self._history(JsonFile.read(self.json_path))
        history.append(entry)
        JsonFile.write(self.json_path, history)
        self.last_backend = "json"
        return entry