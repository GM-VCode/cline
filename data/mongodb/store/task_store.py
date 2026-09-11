# ============================================================
#  data/mongodb/store/task_store.py — class TaskStore (fachada)
#  Compõe RuntimePaths + MongoConnection + StateRepo + dois
#  HistoryCollection (validations, diagnostics). Mantém a API
#  pública: save/load state, append/list validations e diagnostics.
# ============================================================

import os
import time
from typing import Any

from data.mongodb.connection import MongoConnection
from data.mongodb.store.runtime import RuntimePaths
from data.mongodb.store.state import StateRepo
from data.mongodb.store.history import HistoryCollection


class TaskStore:
    """Memória do agente: estado + históricos (Mongo com fallback JSON)."""

    def __init__(self, uri: str | None = None, db: str | None = None,
                 state_path: str | None = None,
                 validations_path: str | None = None,
                 timeout_ms: int = 2000,
                 model_name: str | None = None) -> None:
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
        # Benchmarks: coleção ÚNICA; 1 doc por modelo (chave = model_name)
        # com o histórico de corridas agrupado no timeline do doc.
        self.model_name = model_name or ""

        self._conn: MongoConnection = MongoConnection(
            self.uri, self.db_name, timeout_ms
        )
        self._error: str | None = None
        self._error = self._conn.error
        self._log_fallback()

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

    def _catch_error(self, msg: str) -> None:
        self._error = msg
        self._log_fallback(extra=f"erro em runtime: {msg}")

    def _log_fallback(self, extra: str | None = None) -> None:
        """Registra em logs/app/fallback.log quando o MongoDB não está
        disponível e o fallback JSON/temp entra em ação (auditoria).
        Import lazy: nunca deixa o logging quebrar o store.
        """
        if self._conn and self._conn.active:
            return
        try:
            from app.agent.debug import get_fallback_logger
            log = get_fallback_logger()
            if log:
                motivo = self._error or "desconhecido"
                destino = self.paths.state_path
                log.warn(f"FALLBACK ATIVADO Mongo indisponível "
                         f"(motivo: {motivo}) → JSON/temp: {destino}")
                if extra:
                    log.warn(f"FALLBACK {extra}")
        except Exception:  # pragma: no cover - logging nunca quebra o store
            pass

    @property
    def active(self) -> bool:
        return bool(self._conn and self._conn.active)

    @property
    def error(self) -> str | None:
        return self._error

    # ---------- estado ----------
    def save_state(self, payload: dict[str, Any], task_id: str | None = None) -> dict[str, Any]:
        return self.state.save(payload, task_id=task_id)

    def load_state(self, task_id: str | None = None) -> dict[str, Any]:
        return self.state.load(task_id=task_id)

    # ---------- validações ----------
    def append_validation(self, entry: dict[str, Any]) -> dict[str, Any]:
        return self.validations.append(entry)

    def list_validations(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.validations.list(limit)

    # ---------- diagnósticos ----------
    def append_diagnostic(self, entry: dict[str, Any]) -> dict[str, Any]:
        return self.diagnostics.append(entry)

    def list_diagnostics(self, limit: int = 20) -> list[dict[str, Any]]:
        return self.diagnostics.list(limit)

    # ---------- benchmarks ----------
    def _bench_model(self) -> str:
        """Chave única do modelo nos docs de benchmark_runs."""
        return self.model_name or "unknown"

    def append_benchmark(self, entry: dict[str, Any]) -> dict[str, Any]:
        """Grava 1 corrida no doc do modelo (1 doc por model em
        benchmark_runs; corridas agrupadas no timeline do doc)."""
        modelo = self._bench_model()
        entry.setdefault("model", modelo)
        ts = entry.setdefault(
            "ts", time.strftime("%Y-%m-%dT%H:%M:%S"))
        return self.benchmarks.upsert(
            {"model": modelo, "last_run": ts},
            task_id=f"bench:{modelo}", event=entry)

    def list_benchmarks(self, limit: int = 20) -> list[dict[str, Any]]:
        """Docs por modelo (model + timeline de corridas)."""
        return self.benchmarks.list(limit, task_id=f"bench:{self._bench_model()}")

    # ---------- execuções do agente ----------
    def append_agent_run(self, entry: dict[str, Any],
                         task_id: str | None = None) -> dict[str, Any]:
        return self.agent_runs.append(entry, task_id=task_id)

    def upsert_agent_run(self, entry: dict[str, Any], task_id: str | None = None,
                         event: dict[str, Any] | None = None) -> dict[str, Any]:
        """1 documento por conversa: atualiza o doc do task_id ou cria.

        Mantém o agente_runs limpo (sem duplicatas por request). É a forma
        usada pelo proxy, em que toda requisição da mesma conversa
        sobrescreve o mesmo registro com status atualizado. ``event``
        (opcional) é anexado à timeline da conversa (event sourcing).
        """
        return self.agent_runs.upsert(entry, task_id=task_id, event=event)

    def get_agent_run(self, task_id: str | None = None) -> dict[str, Any] | None:
        """Documento único da conversa no agent_runs (ou None)."""
        return self.agent_runs.get_one(task_id)

    def list_agent_runs(self, limit: int = 20,
                        task_id: str | None = None) -> list[dict[str, Any]]:
        return self.agent_runs.list(limit, task_id=task_id)

    def close(self) -> None:
        self._conn.close()