# ============================================================
#  data/mongodb/scripts/memory.py — CLI da memória
#  Consulta o estado atual da tarefa e o histórico de validações.
#  Uso: python data/mongodb/scripts/memory.py state
#       python data/mongodb/scripts/memory.py validations [N]
# ============================================================

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from data.mongodb.store import TaskStore  # noqa: E402


class MemoryCli:
    """Acceso por terminal a la memoria persistente."""

    def __init__(self, store: TaskStore):
        self.store = store

    def _state(self) -> int:
        state = self.store.load_state()
        if not state:
            print("Nenhum estado guardado ainda.")
            return 0
        print("=== ESTADO DA TAREFA ===")
        print("objetivo:", state.get("objective", "-"))
        print("task_id :", state.get("task_id", "-"))
        print("atualizado:", state.get("updated_at", "-"))
        for s in state.get("plan", []):
            print(f"  [{s.get('status', '?')}] {s.get('id', '?')}: "
                  f"{s.get('description', '')}")
        print("próxima ação:", state.get("next_action", "-"))
        return 0

    def _validations(self, limit: int) -> int:
        vals = self.store.list_validations(limit=limit)
        if not vals:
            print("Nenhuma validação registrada ainda.")
            return 0
        print(f"=== ÚLTIMAS {len(vals)} VALIDAÇÕES ===")
        for v in vals:
            print(f"  [{v.get('ts', '?')}] {v.get('phase', '?')} -> "
                  f"{v.get('result', '?')} (exit {v.get('exit_code', '?')})")
        return 0

    def _diagnostics(self, limit: int) -> int:
        diags = self.store.list_diagnostics(limit=limit)
        if not diags:
            print("Nenhum diagnóstico registrado ainda (rode doctor.py).")
            return 0
        print(f"=== ÚLTIMOS {len(diags)} DIAGNÓSTICOS ===")
        for d in diags:
            print(f"  [{d.get('ts', '?')}] {d.get('verdict', '?')} "
                  f"(fails={d.get('fails', '?')}, warns={d.get('warns', '?')})")
        return 0

    def run(self, argv) -> int:
        cmd = argv[0] if argv else "state"
        if cmd == "state":
            return self._state()
        if cmd == "validations":
            limit = int(argv[1]) if len(argv) > 1 else 20
            return self._validations(limit)
        if cmd == "diagnostics":
            limit = int(argv[1]) if len(argv) > 1 else 20
            return self._diagnostics(limit)
        print("Uso: memory.py [state|validations|diagnostics [N]]")
        return 2


def main() -> int:
    uri = os.environ.get("MONGODB_URI", "") or "mongodb://localhost:27017/"
    store = TaskStore(uri=uri)
    rc = MemoryCli(store).run(sys.argv[1:])
    store.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())