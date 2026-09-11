# ============================================================
#  tools/agent_test.py — teste ponta a ponta do agente
#  Dá UMA tarefa simples ao agente (AgentRunner + modelo real),
#  verifica com um comando real e REGISTRA nos dois lugares:
#    tasks      → save_state (status completed/failed)
#    agent_runs → upsert com finished True/False
#  Ao final imprime os dois registros, puxados DE VOLA do banco.
#
#  Uso:  .venv\Scripts\python.exe tools\agent_test.py
#        (modelo precisa estar no ar: python main.py)
# ============================================================

import argparse
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()

from app.agent.debug import get_agent_logger  # noqa: E402
from app.agent.identity import AgentIdentity  # noqa: E402
from app.agent.runner.core import AgentRunner  # noqa: E402
from tools.benchmarks.executor_llama import LlamaExecutor  # noqa: E402

#: tarefa padrão: simples, verificável de verdade
TAREFA = ("Crie o arquivo saudacao.py com uma função saudar(nome) "
          "que retorna a string 'Olá, <nome>!' (ex.: saudar('Vini') "
          "retorna 'Olá, Vini!'). Use type hints.")
CHECK_CMD = [sys.executable, "-c",
             "import saudacao; r = saudacao.saudar('Vini'); "
             "assert r == 'Olá, Vini!', r; print('CHECK OK:', r)"]
TASK_ID = "agent-task-test"


class AgentTaskTest:
    """Roda 1 tarefa com o agente e audita tasks + agent_runs."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.store = None

    # ---------- setup / teardown ----------
    def _projeto(self) -> str:
        pasta = ProjectPath.join("temp", "agent_task_test")
        shutil.rmtree(pasta, ignore_errors=True)
        os.makedirs(pasta, exist_ok=True)
        return pasta

    def _store(self):
        if self.args.no_memory:
            return None
        try:
            from app import TaskStore
            self.store = TaskStore()
        except Exception as exc:
            print(f"AVISO: TaskStore indisponível ({exc}) — sem tasks/agent_runs")
        return self.store

    # ---------- execução ----------
    def run(self) -> int:
        project = self._projeto()
        store = self._store()
        log = get_agent_logger()
        runner = AgentRunner(
            LlamaExecutor(temperature=self.args.temperature),
            check_cmd=CHECK_CMD,
            max_attempts=self.args.attempts,
            identity=None if self.args.no_identity else AgentIdentity(),
            store=store,
        )
        started = time.time()
        result = runner.run(self.args.instruction, project)
        elapsed = round(time.time() - started, 2)

        # agent_runs: registro com finished True/False (1 doc por task_id)
        if store is not None:
            store.upsert_agent_run({
                "source": "agent_test",
                "instruction": self.args.instruction,
                "status": "completed" if result["finished"] else "failed",
                "finished": result["finished"],
                "attempts": result["attempts"],
                "retries": result["retries"],
                "files": result.get("files_written", []),
                "elapsed_s": result["elapsed_s"],
                "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            }, task_id=TASK_ID,
                event={"tipo": "run", "nota": f"agent_test {elapsed}s"})

        self._relatorio(result, store, project)
        return 0 if result["finished"] else 1

    # ---------- relatório ----------
    @staticmethod
    def _relatorio(result: dict, store, project: str) -> None:
        print("=" * 62)
        print("  TESTE DO AGENTE — resultado")
        print("=" * 62)
        print(f"  finalizado : {result['finished']}   "
              f"(tentativas={result['attempts']}, retries={result['retries']})")
        print(f"  arquivos   : {result.get('files_written', [])}")
        if result.get("error"):
            print(f"  erro       : {str(result['error'])[:200]}")
        print(f"  projeto    : {project}")
        if store is None:
            print("  (memória desativada: nada em tasks/agent_runs)")
            return
        state = store.load_state() or {}
        run = store.get_agent_run(TASK_ID) or {}
        print("-" * 62)
        print(f"  tasks (coleção 'tasks'):")
        print(f"    status        : {state.get('status', '?')}")
        print(f"    finished      : "
              f"{(state.get('last_result') or {}).get('finished', '?')}")
        print(f"  agent_runs (task_id={TASK_ID}):")
        print(f"    finished      : {run.get('finished', '?')}")
        print(f"    status        : {run.get('status', '?')}")
        print(f"    attempts      : {run.get('attempts', '?')}  "
              f"retries: {run.get('retries', '?')}")
        print("=" * 62)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Teste ponta a ponta do agente: tasks + agent_runs")
    ap.add_argument("--instruction", default=TAREFA,
                    help="tarefa alternativa para o agente")
    ap.add_argument("--attempts", type=int, default=2)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--no-identity", action="store_true")
    ap.add_argument("--no-memory", action="store_true")
    args = ap.parse_args()
    return AgentTaskTest(args).run()


if __name__ == "__main__":
    sys.exit(main())
