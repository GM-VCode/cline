# ============================================================
#  data/mongodb/scripts/init_mongo.py — INIT da memoria Mongo
#  Cria coleções e índices da base cline_agent no MongoDB local.
#  Uso: python data/mongodb/scripts/init_mongo.py
# ============================================================

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.mongodb.connection import MongoConnection  # noqa: E402


class MongoInitializer:
    """Prepara o MongoDB: cria coleções e índices."""

    def __init__(self, uri: str, db: str = "cline_agent"):
        self.uri = uri
        self.db = db

    def run(self) -> int:
        conn = MongoConnection(self.uri, self.db)
        if not conn.active:
            print("FALLO: não consegui conectar ao MongoDB.")
            print("  ->", conn.error or "sem detalhes")
            print("Certifica-te de que MongoDB corre en localhost:27017")
            return 1
        tasks = conn.collection("tasks")
        validations = conn.collection("validations")
        tasks.create_index("task_id", unique=True)
        validations.create_index([("task_id", 1), ("_id", -1)])
        print("MongoDB OK")
        print("  DB ..........", self.db)
        print("  Collections .. tasks, validations")
        conn.close()
        return 0


def main() -> int:
    uri = os.environ.get("MONGODB_URI", "") or "mongodb://localhost:27017/"
    return MongoInitializer(uri).run()


if __name__ == "__main__":
    sys.exit(main())
