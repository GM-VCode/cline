# data/mongodb — capa de persistencia (MongoDB local)
#
#  Todo lo relacionado con la base de datos vive aquí, modularizado
#  en archivos pequeños, cada uno con su clase y función:
#    connection.py  -> class MongoConnection (conexión/colecciones)
#    store.py       -> class TaskStore (estado + validações, con fallback JSON)
#    scripts/       -> CLIs (init_mongo, memory)
#
#  El paquete `app.task_store` re-exporta TaskStore para mantener
#  la API pública compatible (from app import TaskStore).

from data.mongodb.connection import MongoConnection  # noqa: F401
from data.mongodb.store import TaskStore             # noqa: F401

__all__ = ["MongoConnection", "TaskStore"]