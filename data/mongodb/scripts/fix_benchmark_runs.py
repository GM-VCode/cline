# ============================================================
#  scripts/fix_benchmark_runs.py — Rebuild do doc por modelo
#  1) Reconstrói o doc bench:<model> com timeline limpo (sem _id)
#  2) Apaga todo doc legado plano (sem campo "model")
#  Fica só: benchmark_runs = {doc por modelo com corridas dele}
#
#  Uso: .venv\Scripts\python.exe data\mongodb\scripts\fix_benchmark_runs.py
# ============================================================

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..")))

from data.mongodb.connection import MongoConnection  # noqa: E402
from data.mongodb.store.runtime import RuntimePaths  # noqa: E402
from project_path import Config  # noqa: E402


def model_key() -> str:
    """Nome único do modelo atual (do gguf): ex. 'Q8_0'."""
    arquivo = os.path.splitext(os.path.basename(Config().MODEL_PATH))[0]
    return arquivo.split("-")[-1].strip() or "unknown"


def main() -> int:
    paths = RuntimePaths()
    conn = MongoConnection(paths.uri, paths.db_name, timeout_ms=4000)
    if not conn.active:
        print("FALLO: MongoDB indisponível")
        return 1
    modelo = model_key()
    col = conn.collection("benchmark_runs")
    assert col is not None

    tid = f"bench:{modelo}"
    corridas: list[dict[str, object]] = []

    # 1) Corridas já agrupadas (doc antigo), limpas e sem duplicatas
    doc = col.find_one({"task_id": tid})
    for run in (doc or {}).get("timeline", []):
        limpo = {k: v for k, v in run.items() if k != "_id"}
        if limpo not in corridas:
            corridas.append(limpo)

    # 2) Corridas planas legadas (sem campo model) — assume o modelo atual
    planos = list(col.find({"model": {"$exists": False},
                            "task_id": {"$ne": tid}}))
    for run in planos:
        limpo = {k: v for k, v in run.items() if k != "_id"}
        limpo.setdefault("model", modelo)
        if limpo not in corridas:
            corridas.append(limpo)
    corridas.sort(key=lambda d: str(d.get("ts", "")))

    col.update_one({"task_id": tid}, {"$set": {
        "task_id": tid,
        "model": modelo,
        "last_run": str(corridas[-1].get("ts", "")) if corridas else "",
        "timeline": corridas,
    }}, upsert=True)
    print(f"OK: doc {tid} reconstruído com {len(corridas)} corrida(s)")

    # 3) Apaga tudo que não é doc por modelo
    removidos = col.delete_many({"task_id": {"$ne": tid}})
    print(f"OK: {removidos.deleted_count} doc(s) fora do formato apagado(s)")
    print(f"    restantes em benchmark_runs: {col.count_documents({})}")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
