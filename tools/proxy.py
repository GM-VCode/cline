# ============================================================
#  tools/proxy.py — CLI do proxy de memória
#  Sobe o proxy OpenAI-Compatible: Cline -> :8081 -> llama-server.
#  Cada tarefa do Cline é gravada no Mongo (tasks + agent_runs).
#
#  Uso:
#    python tools/proxy.py [--host 127.0.0.1] [--port 8081]
#                          [--upstream http://127.0.0.1:8080]
#                          [--no-memory]
# ============================================================

import argparse
import os
import sys
from typing import TYPE_CHECKING

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()

from app.agent.debug import get_agent_logger  # noqa: E402
from app.services.proxy import ProxyServer  # noqa: E402

if TYPE_CHECKING:
    from app.task_store import TaskStore


class ProxyCLI:
    """Ponto de entrada do proxy pela linha de comando."""

    def __init__(self, argv: list[str] | None = None) -> None:
        self.args = self._parse(argv)

    @staticmethod
    def _parse(argv: list[str] | None) -> argparse.Namespace:
        p = argparse.ArgumentParser(
            description="Proxy de memória: Cline -> llama-server -> Mongo")
        p.add_argument("--host", default="127.0.0.1",
                       help="interface do proxy (default 127.0.0.1)")
        p.add_argument("--port", type=int, default=8081,
                       help="porta do proxy (default 8081)")
        p.add_argument("--upstream", default="http://127.0.0.1:8080",
                       help="URL do llama-server (default :8080)")
        p.add_argument("--no-memory", action="store_true",
                       help="só repassar; não gravar no Mongo/JSON")
        return p.parse_args(argv)

    def _make_store(self) -> "TaskStore | None":
        if self.args.no_memory:
            return None
        try:
            from app import TaskStore
            return TaskStore()
        except Exception as exc:
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: TaskStore não criado ({exc})")
            return None

    def _report_memory(self, store: "TaskStore | None") -> None:
        log = get_agent_logger()
        if store is None:
            motivo = ("--no-memory" if self.args.no_memory
                      else "falha ao criar o TaskStore")
            msg = f"memória: DESATIVADA ({motivo})"
        elif store.active:
            msg = (f"memória: Mongo ATIVO (db={store.db_name}, "
                   f"task_id={store.task_id})")
        else:
            msg = (f"memória: Mongo INDISPONÍVEL -> fallback JSON "
                   f"({store.error})")
        print(msg)
        if log:
            log.info("proxy: " + msg)

    def run(self) -> int:
        store = self._make_store()
        self._report_memory(store)
        server = ProxyServer(host=self.args.host, port=self.args.port,
                             upstream=self.args.upstream, store=store)
        print(f"PROXY PRONTO: http://{self.args.host}:{self.args.port}"
              f" -> {self.args.upstream}")
        log = get_agent_logger()
        if log:
            log.info(f"proxy: PRONTO http://{self.args.host}:"
                     f"{self.args.port} -> {self.args.upstream}")
        try:
            server.run(blocking=True)
        except KeyboardInterrupt:
            print("\nproxy encerrado")
        finally:
            server.close()
        return 0


if __name__ == "__main__":
    sys.exit(ProxyCLI().run())
