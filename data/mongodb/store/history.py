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

    def upsert(self, entry: dict, task_id: str | None = None,
               event: dict | None = None) -> dict:
        """Atualiza o registro existente da conversa ou cria se não existir.

        Mantém exatamente 1 documento por task_id (não acumula duplicatas):
        se o registro já existiu, os campos de ``entry`` sobrescrevem os
        antigos e ``ts``/``last_update`` refletem o request mais recente.
        ``event`` (opcional) é anexado à timeline (event sourcing).
        """
        if not isinstance(entry, dict):
            entry = {"value": entry}
        entry = dict(entry)
        tid = task_id or self.task_id
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        entry.setdefault("task_id", tid)
        entry.setdefault("ts", now)
        coll = self._coll
        if coll is not None:
            try:
                sets = dict(entry)
                sets["last_update"] = now
                # created_at vem do doc base; nunca pode estar em $set E
                # $setOnInsert ao mesmo tempo (conflito no MongoDB).
                created = sets.pop("created_at", now)
                update = {"$set": sets,
                          "$setOnInsert": {"created_at": created}}
                if event is not None:
                    update["$push"] = {"timeline": event}
                coll.update_one({"task_id": tid}, update, upsert=True)
                self.last_backend = "mongo"
                return sets
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (upsert {self.coll_name}): {exc}")
        return self._upsert_json(entry, tid, event)

    def _upsert_json(self, entry: dict, tid: str,
                     event: dict | None = None) -> dict:
        history = JsonFile.read(self.json_path)
        if not isinstance(history, list):
            history = []
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        for i, old in enumerate(history):
            if isinstance(old, dict) and old.get("task_id") == tid:
                merged = dict(old)
                merged.update(entry)
                if event is not None:
                    timeline = list(merged.get("timeline") or [])
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

    def get_one(self, task_id: str | None = None) -> dict | None:
        """Documento único da conversa (None se ainda não existe)."""
        tid = task_id or self.task_id
        coll = self._coll
        if coll is not None:
            try:
                doc = coll.find_one({"task_id": tid})
                if doc is None:
                    return None
                return {k: v for k, v in doc.items() if k != "_id"}
            except Exception as exc:  # pragma: no cover
                self.error_sink(f"Falha Mongo (get_one {self.coll_name}): {exc}")
        history = JsonFile.read(self.json_path)
        if not isinstance(history, list):
            return None
        for e in reversed(history):
            if isinstance(e, dict) and e.get("task_id") == tid:
                return e
        return None

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