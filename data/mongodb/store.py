# ============================================================
#  data/mongodb/store.py — class TaskStore
#  Orquesta el guardado del estado de la tarefa y el histórico de
#  validações. Usa MongoConnection si hay Mongo; si no, fallback a
#  archivos JSON en data/json/.
# ============================================================

import json
import os
import time

try:
    from data.mongodb.connection import MongoConnection
except ImportError:  # pragma: no cover
    MongoConnection = None


class TaskStore:
    """Estado + histórico con persistencia Mongo y fallback JSON."""

    def __init__(self, uri=None, db=None, state_path=None,
                 validations_path=None, timeout_ms=2000):
        root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        env = self._env(root)
        data_dir = os.path.join(root, "data", "json")
        os.makedirs(data_dir, exist_ok=True)

        if uri is None:
            uri = env.get("MONGODB_URI", "") or os.environ.get("MONGODB_URI", "")
        if db is None:
            db = (env.get("MONGODB_DB", "") or os.environ.get("MONGODB_DB", "")
                  or "cline_agent")
        self.uri = uri or "mongodb://localhost:27017/"
        self.db_name = db
        self.task_id = (env.get("TASK_ID", "") or os.environ.get("TASK_ID", "")
                        or "current")
        self.state_path = state_path or os.path.join(data_dir, "task-state.json")
        self.validations_path = validations_path or os.path.join(
            data_dir, "validations.json")

        self._conn = None
        self._error = None
        if MongoConnection is not None:
            self._conn = MongoConnection(self.uri, self.db_name, timeout_ms)
            self._error = self._conn.error

    # ---------- helpers ----------
    @staticmethod
    def _env(root):
        """Lê el .env reutilizando el parser de Config (sin tocar nada)."""
        try:
            from app.config import Config as _Config
            return _Config._load_dotenv(os.path.join(root, ".env"))
        except Exception:
            return {}

    @staticmethod
    def _read_json(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    @staticmethod
    def _write_json(path, data):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except OSError:
            pass

    @property
    def active(self) -> bool:
        """True si MongoConnection está conectado."""
        return bool(self._conn and self._conn.active)

    @property
    def error(self):
        return self._error

    @property
    def tasks_coll(self):
        return self._conn.collection("tasks") if self._conn else None

    @property
    def validations_coll(self):
        return self._conn.collection("validations") if self._conn else None

    # ---------- estado ----------
    def save_state(self, payload: dict) -> dict:
        if not isinstance(payload, dict):
            payload = {}
        payload = dict(payload)
        payload.setdefault("task_id", self.task_id)
        payload.setdefault("updated_at",
                           time.strftime("%Y-%m-%dT%H:%M:%S"))
        if self.active:
            try:
                self.tasks_coll.replace_one({"task_id": self.task_id},
                                            payload, upsert=True)
            except Exception as exc:  # pragma: no cover
                self._error = f"Falha Mongo (save_state): {exc}"
        self._write_json(self.state_path, payload)
        return payload

    def load_state(self) -> dict:
        if self.active:
            try:
                doc = self.tasks_coll.find_one({"task_id": self.task_id})
                if doc:
                    return {k: v for k, v in doc.items() if k != "_id"}
            except Exception as exc:  # pragma: no cover
                self._error = f"Falha Mongo (load_state): {exc}"
        data = self._read_json(self.state_path)
        return data if isinstance(data, dict) else {}

    # ---------- validações ----------
    def append_validation(self, entry: dict) -> dict:
        """Registra una corrida. Con Mongo ativo, SOLO Mongo; sin Mongo, JSON."""
        if not isinstance(entry, dict):
            entry = {"result": entry}
        entry = dict(entry)
        entry.setdefault("task_id", self.task_id)
        entry.setdefault("ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        if self.active:
            try:
                self.validations_coll.insert_one(dict(entry))
                return entry
            except Exception as exc:  # pragma: no cover
                self._error = f"Falha Mongo (append_validation): {exc}"
        history = self._read_json(self.validations_path)
        if not isinstance(history, list):
            history = []
        history.append(entry)
        self._write_json(self.validations_path, history)
        return entry

    def list_validations(self, limit: int = 20) -> list:
        if self.active:
            try:
                cursor = (self.validations_coll
                          .find({"task_id": self.task_id})
                          .sort("_id", -1).limit(limit))
                out = []
                for r in cursor:
                    r.pop("_id", None)
                    out.append(r)
                return out
            except Exception as exc:  # pragma: no cover
                self._error = f"Falha Mongo (list_validations): {exc}"
        history = self._read_json(self.validations_path)
        if not isinstance(history, list):
            return []
        return list(reversed(history[-limit:]))

    def close(self):
        if self._conn is not None:
            self._conn.close()