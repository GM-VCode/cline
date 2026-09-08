# ============================================================
#  data/mongodb/store/task_store.py — class TaskStore (fachada)
#  Compõe RuntimePaths + MongoConnection + StateRepo + dois
#  HistoryCollection (validations, diagnostics). Mantém a API
#  pública: save/load state, append/list validations e diagnostics.
# ============================================================

import os

try:
    from data.mongodb.connection import MongoConnection
except ImportError:  # pragma: no cover
    MongoConnection = None

from data.mongodb.store.runtime import RuntimePaths
from data.mongodb.store.state import StateRepo
from data.mongodb.store.history import HistoryCollection


class TaskStore:
    """Memória do agente: estado + históricos (Mongo com fallback JSON)."""

    def __init__(self, uri=None, db=None, state_path=None,
                 validations_path=None, timeout_ms=2000):
        self.paths = RuntimePaths()
        if uri:
            self.paths.uri = uri
        if db:
            self.paths.db_name = db
        if state_path:
            self.paths.state_path = state_path
        if validations_path:
            self.paths.validations_path = validations_path
            # históricos derivados vivem na mesma pasta do runtime informado
            base = os.path.dirname(validations_path)
            self.paths.diagnostics_path = os.path.join(base, "diagnostics.json")
            self.paths.benchmarks_path = os.path.join(base, "benchmarks.json")
            self.paths.agent_runs_path = os.path.join(base, "agent_runs.json")
        self.task_id = self.paths.task_id
        self.uri = self.paths.uri
        self.db_name = self.paths.db_name

        self._conn = None
        self._error = None
        if MongoConnection is not None:
            self._conn = MongoConnection(self.uri, self.db_name, timeout_ms)
            self._error = self._conn.error

        self.state = StateRepo(
            self._conn, self.paths.state_path, self.task_id,
            error_sink=self._catch_error)
        self.validations = HistoryCollection(
            self._conn, "validations", self.paths.validations_path,
            "validation", self.task_id, self._catch_error)
        self.diagnostics = HistoryCollection(
            self._conn, "diagnostics", self.paths.diagnostics_path,
            "diagnostic", self.task_id, self._catch_error)
        self.benchmarks = HistoryCollection(
            self._conn, "benchmark_runs", self.paths.benchmarks_path,
            "benchmark", self.task_id, self._catch_error)
        self.agent_runs = HistoryCollection(
            self._conn, "agent_runs", self.paths.agent_runs_path,
            "agent_run", self.task_id, self._catch_error)

    def _catch_error(self, msg: str):
        self._error = msg

    @property
    def active(self) -> bool:
        return bool(self._conn and self._conn.active)

    @property
    def error(self):
        return self._error

    # ---------- estado ----------
    def save_state(self, payload: dict) -> dict:
        return self.state.save(payload)

    def load_state(self) -> dict:
        return self.state.load()

    # ---------- validações ----------
    def append_validation(self, entry: dict) -> dict:
        return self.validations.append(entry)

    def list_validations(self, limit: int = 20) -> list:
        return self.validations.list(limit)

    # ---------- diagnósticos ----------
    def append_diagnostic(self, entry: dict) -> dict:
        return self.diagnostics.append(entry)

    def list_diagnostics(self, limit: int = 20) -> list:
        return self.diagnostics.list(limit)

    # ---------- benchmarks ----------
    def append_benchmark(self, entry: dict) -> dict:
        return self.benchmarks.append(entry)

    def list_benchmarks(self, limit: int = 20) -> list:
        return self.benchmarks.list(limit)

    # ---------- execuções do agente ----------
    def append_agent_run(self, entry: dict) -> dict:
        return self.agent_runs.append(entry)

    def list_agent_runs(self, limit: int = 20) -> list:
        return self.agent_runs.list(limit)

    def close(self):
        if self._conn is not None:
            self._conn.close()