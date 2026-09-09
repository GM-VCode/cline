# ============================================================
#  app/services/proxy/server.py — class ProxyServer
#  ThreadingHTTPServer que expõe o ProxyHandler. Configura os
#  atributos de classe do handler (store/upstream/sessions).
# ============================================================

import threading
from http.server import ThreadingHTTPServer
from typing import TYPE_CHECKING

from app.services.proxy.handler import ProxyHandler
from app.services.proxy.loopguard import LoopGuard
from app.services.proxy.sessions import SessionRegistry

if TYPE_CHECKING:  # anotação só para o editor (não roda em runtime)
    from app.task_store import TaskStore


class ProxyServer:
    """Proxy HTTP (threaded) entre o Cline e o llama-server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8081,
                 upstream: str = "http://127.0.0.1:8080",
                 store: "TaskStore | None" = None) -> None:
        self.host = host
        self.port = port
        self.upstream = upstream
        self.store = store
        self.sessions = SessionRegistry()
        self.loopguard = LoopGuard()
        self._httpd: ThreadingHTTPServer | None = None

    def _configure_handler(self) -> None:
        ProxyHandler.upstream = self.upstream
        ProxyHandler.store = self.store
        ProxyHandler.sessions = self.sessions
        ProxyHandler.loopguard = self.loopguard

    def run(self, blocking: bool = True):
        """Sobe o servidor. blocking=False devolve a thread (p/ testes)."""
        self._configure_handler()
        self._httpd = ThreadingHTTPServer((self.host, self.port),
                                          ProxyHandler)
        if blocking:
            self._httpd.serve_forever()
            return None
        thread = threading.Thread(target=self._httpd.serve_forever,
                                  daemon=True)
        thread.start()
        return thread

    def close(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
