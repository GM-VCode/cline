# ============================================================
#  data/mongodb/connection.py — class MongoConnection
#  Encapsula la conexión a MongoDB local y el acceso a coleções.
#  Fino: solo conecta/exponhe. Sin lógica de negocio.
# ============================================================

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from typing import Any


class MongoConnection:
    """Wraper fino a MongoDB: conexión, ping y colecciones."""

    def __init__(self, uri: str, db_name: str = "cline_agent",
                 timeout_ms: int = 2000) -> None:
        self.uri = uri
        self.db_name = db_name
        self._client: MongoClient | None = None
        self._db: Database | None = None
        self.error: str | None = None
        self._connect(timeout_ms)

    def _connect(self, timeout_ms: int) -> None:
        client = None
        try:
            client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=timeout_ms,
                connectTimeoutMS=min(timeout_ms, 2000),
            )
            client.admin.command("ping")
            self._client = client
            self._db = client[self.db_name]
        except Exception as exc:  # pragma: no cover
            if client is not None:
                try:
                    client.close()
                except Exception:
                    pass
            self.error = f"Mongo indisponible: {exc}"
            self._log_failure(exc)

    def _log_failure(self, exc: Exception) -> None:
        """Loga a falha de conexão (import lazy, nunca levanta)."""
        try:
            from app.agent.debug import get_fallback_logger
            log = get_fallback_logger()
            if log:
                log.error(f"MongoConnection falhou em {self.uri}: {exc}")
        except Exception:  # pragma: no cover — logging nunca quebra a conexão
            pass

    @property
    def active(self) -> bool:
        """True si hay conexión válida."""
        return self._client is not None

    def collection(self, name: str) -> Collection[dict[str, Any]] | None:
        """Acceso a una colección (tasks, validations...)."""
        return self._db[name] if self._db is not None else None

    def close(self) -> None:
        """Cierra la conexión si estaba abierta."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass