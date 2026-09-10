# ============================================================
#  scripts/migrate_benchmarks.py — Agrupa corridas por modelo
#  benchmark_runs passa a ter 1 doc POR MODELO (task_id=bench:<model>,
#  campo "model" único) com o histórico de corridas no "timeline".
#  Premissa do dono do projeto: todas as corridas antigas são do Q8_0.
#
#  Uso: .venv\Scripts\python.exe data\mongodb\scripts\migrate_benchmarks.py
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

    # Remove artefato da 1.ª versão da migração (coleção por modelo)
    c_q8 = conn.collection("benchmark_runs_Q8_0")
    if c_q8 is not None:
        c_q8.drop()

    antigos = list(col.find({"model": {"$exists": False}}))
    antigos.sort(key=lambda d: d.get("ts", ""))
    if antigos:
        doc = {
            "task_id": f"bench:{modelo}",
            "model": modelo,
            "last_run": antigos[-1].get("ts", ""),
            "timeline": antigos,
        }
        col.update_one({"task_id": f"bench:{modelo}"},
                       {"$set": doc}, upsert=True)
    print(f"OK: {len(antigos)} corrida(s) agrupada(s) no doc do modelo "
          f"{modelo} (task_id=bench:{modelo})")
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
