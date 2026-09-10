# ============================================================
#  tools/agent.py — class AgentCLI
#  CLI do agente real: roda uma instrução num projeto com o
#  modelo local e valida com um comando de verificação.
#
#  Uso (--check é OBRIGATORIO):
#    python tools/agent.py --project <dir> --instruction "..."
#                          --check "python -m pytest -q"
# ============================================================

import argparse
import os
import sys
from typing import TYPE_CHECKING

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()

from app.agent import AgentIdentity, AgentRunner  # noqa: E402
from app.agent.debug import get_agent_logger  # noqa: E402
from tools.benchmarks.executor_llama import LlamaExecutor  # noqa: E402

if TYPE_CHECKING:
    from data.mongodb.store import TaskStore
    from tools.logger import AppLogger


class AgentCLI:
    """Ponto de entrada do agente pela linha de comando."""

    def __init__(self, argv: list[str] | None = None) -> None:
        self.args = self._parse(argv)

    @staticmethod
    def _parse(argv: list[str] | None) -> argparse.Namespace:
        p = argparse.ArgumentParser(
            description="Agente: modelo local + verificação real")
        p.add_argument("--project", required=True,
                       help="diretório do projeto alvo")
        p.add_argument("--instruction", required=True,
                       help="o que o modelo deve fazer")
        p.add_argument("--check",
                       required=True,
                       help="comando de verificação (string; obrigatório — "
                            "executado via shell no projeto; sem --check "
                            "o agente não pode auto-validar e se recusa)")
        p.add_argument("--max-attempts", type=int, default=2)
        p.add_argument("--max-actions", type=int, default=None,
                       help="ativa modo iterativo (ação->observação, "
                            "protocolo 11c) com esse orçamento de passos")
        p.add_argument("--temperature", type=float, default=0.2)
        p.add_argument("--no-context", action="store_true",
                       help="não incluir o contexto do projeto no prompt")
        p.add_argument("--no-identity", action="store_true",
                       help="não incluir o prompt de identidade")
        p.add_argument("--no-memory", action="store_true",
                       help="não registrar a execução no Mongo/JSON")
        return p.parse_args(argv)

    @staticmethod
    def _say(msg: str, log: "AppLogger | None") -> None:
        """Mostra no console e registra em logs/agent.log."""
        print(msg)
        if log:
            log.info(msg)

    def _memory_report(
        self,
        store: "TaskStore | None",
        log: "AppLogger | None",
    ) -> None:
        """Diagnóstico de memória: Mongo ativo, fallback JSON ou off."""
        if store is None:
            motivo = ("--no-memory" if self.args.no_memory
                      else "falha ao criar o TaskStore")
            self._say(f"memória: DESATIVADA ({motivo})", log)
        elif store.active:
            self._say(f"memória: Mongo ATIVO (db={store.db_name}, "
                      f"task_id={store.task_id})", log)
        else:
            self._say(f"memória: Mongo INDISPONÍVEL -> fallback JSON "
                      f"({store.error})", log)

    def run(self) -> int:
        check_value: object = getattr(self.args, "check", "")
        check_text = check_value if isinstance(check_value, str) else ""
        check_cmd: list[str] = check_text.split() if check_text.strip() else []
        if not check_cmd:
            print("ERRO: --check é obrigatório (comando de verificação).",
                  file=sys.stderr)
            return 2
        executor = LlamaExecutor(temperature=self.args.temperature)
        identity = None if self.args.no_identity else AgentIdentity()
        log = get_agent_logger()
        store = None
        if not self.args.no_memory:
            try:
                from app import TaskStore
                store = TaskStore()
            except Exception as exc:
                store = None
                self._say(f"memória: TaskStore não pôde ser criado "
                          f"({exc})", log)
        self._memory_report(store, log)
        runner = AgentRunner(executor, check_cmd=check_cmd,
                             max_attempts=self.args.max_attempts,
                             use_context=not self.args.no_context,
                             identity=identity, store=store,
                             max_actions=self.args.max_actions)
        result = runner.run(self.args.instruction, self.args.project)
        print(f"finalizado: {result['finished']}  "
              f"tentativas: {result['attempts']}  "
              f"retries: {result['retries']}"
              + (f"  ações: {result.get('actions_used')}"
                 if result.get("actions_used") is not None else ""))
        print(f"arquivos: {result.get('files_written', [])}")
        if result.get("check_output"):
            print(f"verificação: {result['check_output'][:400]}")
        if store is not None:
            self._say(f"registro: tasks->{store.state.last_backend}  "
                      f"agent_runs->{store.agent_runs.last_backend}", log)
        return 0 if result["finished"] else 1


if __name__ == "__main__":
    sys.exit(AgentCLI().run())
