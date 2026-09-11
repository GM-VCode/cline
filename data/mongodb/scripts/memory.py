# ============================================================
#  data/mongodb/scripts/memory.py — CLI da memória
#  Consulta o estado atual da tarefa e o histórico de validações.
#  Uso: python data/mongodb/scripts/memory.py state
#       python data/mongodb/scripts/memory.py validations [N]
# ============================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))))
from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()

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

    def _agent_runs(self, limit: int) -> int:
        # "*" = todas as execuções (qualquer task_id), mais recente primeiro
        runs = self.store.list_agent_runs(limit=limit, task_id="*")
        if not runs:
            print("Nenhuma execução do agente registrada ainda (rode tools/agent.py).")
            return 0
        print(f"=== ÚLTIMAS {len(runs)} EXECUÇÕES DO AGENTE ===")
        for r in runs:
            print(f"  [{r.get('ts', '?')}] finalizado={r.get('finished')} "
                  f"tentativas={r.get('attempts')} retries={r.get('retries')} "
                  f"tempo={r.get('elapsed_s')}s arquivos={r.get('files')}")
            print(f"      instr: {str(r.get('instruction', ''))[:80]}")
        return 0

    def _conversa(self, sid: str) -> int:
        """Mostra a timeline completa de UMA conversa (event sourcing)."""
        doc = self.store.get_agent_run(sid)
        if doc is None:
            print(f"Nenhuma conversa com task_id={sid!r}.")
            print("Dica: use `agent-runs` ou consulte o Mongo por 'source: cline-proxy'.")
            return 1
        print(f"=== CONVERSA {sid} ===")
        print(f"status     : {doc.get('status')}  (finished={doc.get('finished')})")
        print(f"requests   : {doc.get('requests_count')}")
        print(f"instr      : {str(doc.get('instruction', ''))[:120]}")
        print(f"finish_reason (último): {doc.get('last_finish_reason')}")
        print("timeline:")
        for ev in doc.get("timeline", []) or []:
            print(f"  [{ev.get('ts', '?')}] {ev.get('tipo', '?')}: "
                  f"{ev.get('nota', '')}"
                  + (f" ({ev.get('detalhe', '')})" if ev.get("detalhe") else ""))
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
        if cmd == "agent-runs":
            limit = int(argv[1]) if len(argv) > 1 else 20
            return self._agent_runs(limit)
        if cmd == "conversa":
            if len(argv) < 2:
                print("Uso: memory.py conversa <task_id>")
                return 2
            return self._conversa(argv[1])
        print("Uso: memory.py [state|validations|diagnostics|agent-runs|conversa <id>]")
        return 2


def main() -> int:
    uri = os.environ.get("MONGODB_URI", "") or "mongodb://localhost:27017/"
    store = TaskStore(uri=uri)
    if not store.active:
        motivo = store.error or "desconhecido"
        print(f"AVISO: MongoDB indisponível ({motivo}) — lendo do fallback "
              f"JSON ({store.paths.validations_path})")
    rc = MemoryCli(store).run(sys.argv[1:])
    store.close()
    return rc


if __name__ == "__main__":
    sys.exit(main())