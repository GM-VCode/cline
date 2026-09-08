# ============================================================
#  tools/agent.py — class AgentCLI
#  CLI do agente real: roda uma instrução num projeto com o
#  modelo local e valida com um comando de verificação.
#
#  Uso:
#    python tools/agent.py --project <dir> --instruction "..."
#                          --check "python -m pytest -q"
# ============================================================

import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.agent import AgentIdentity, AgentRunner
from tools.benchmarks.executor_llama import LlamaExecutor


class AgentCLI:
    """Ponto de entrada do agente pela linha de comando."""

    def __init__(self, argv: list = None):
        self.args = self._parse(argv)

    @staticmethod
    def _parse(argv):
        p = argparse.ArgumentParser(
            description="Agente: modelo local + verificação real")
        p.add_argument("--project", required=True,
                       help="diretório do projeto alvo")
        p.add_argument("--instruction", required=True,
                       help="o que o modelo deve fazer")
        p.add_argument("--check", default="",
                       help="comando de verificação (string; "
                            "executado via shell no projeto)")
        p.add_argument("--max-attempts", type=int, default=2)
        p.add_argument("--temperature", type=float, default=0.2)
        p.add_argument("--no-context", action="store_true",
                       help="não incluir o contexto do projeto no prompt")
        p.add_argument("--no-identity", action="store_true",
                       help="não incluir o prompt de identidade")
        return p.parse_args(argv)

    def run(self) -> int:
        check_cmd = self.args.check.split() if self.args.check else []
        executor = LlamaExecutor(temperature=self.args.temperature)
        identity = None if self.args.no_identity else AgentIdentity()
        runner = AgentRunner(executor, check_cmd=check_cmd,
                             max_attempts=self.args.max_attempts,
                             use_context=not self.args.no_context,
                             identity=identity)
        result = runner.run(self.args.instruction, self.args.project)
        print(f"finalizado: {result['finished']}  "
              f"tentativas: {result['attempts']}  "
              f"retries: {result['retries']}")
        print(f"arquivos: {result.get('files_written', [])}")
        if result.get("check_output"):
            print(f"verificação: {result['check_output'][:400]}")
        return 0 if result["finished"] else 1


if __name__ == "__main__":
    sys.exit(AgentCLI().run())
