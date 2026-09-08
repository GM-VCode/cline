# ============================================================
#  app/services/proxy/handler.py — class ProxyHandler
#  Recebe o request do Cline, grava a tarefa no Mongo
#  (tasks + agent_runs) e repassa ao llama-server.
#  Streaming SSE sai chunk a chunk (read1 + flush imediato).
# ============================================================

import json
import time
import urllib.error
import uuid
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING
from urllib.request import Request, urlopen

from app.agent.debug import get_agent_logger
from app.services.proxy.sessions import SessionRegistry

if TYPE_CHECKING:  # anotação só para o editor (não roda em runtime)
    from app.task_store import TaskStore


class ProxyHandler(BaseHTTPRequestHandler):
    """Handler HTTP: Cline -> Mongo -> llama-server -> Cline."""

    store: "TaskStore | None" = None  # injetado por ProxyServer
    upstream: str = "http://127.0.0.1:8080"
    sessions: SessionRegistry | None = None
    SKIP_HEADERS = ("host", "content-length", "connection",
                    "accept-encoding", "transfer-encoding")
    UPSTREAM_TIMEOUT = 600  # geração longa não pode estourar cedo

    # ---------- infra ----------
    def log_message(self, fmt, *args):
        log = get_agent_logger()
        if log:
            log.debug("proxy: " + (fmt % args))

    def _send_json(self, code: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- relay ----------
    def _relay_upstream(self, raw: bytes = None) -> None:
        """Repassa ao llama-server e devolve o corpo ao Cline.
        HTTPError (4xx/5xx) é repassado como veio, sem virar 502."""
        headers = {k: v for k, v in self.headers.items()
                   if k.lower() not in self.SKIP_HEADERS}
        headers["Accept-Encoding"] = "identity"
        req = Request(self.upstream + self.path, data=raw,
                      headers=headers,
                      method="POST" if raw is not None else "GET")
        try:
            resp = urlopen(req, timeout=self.UPSTREAM_TIMEOUT)
        except urllib.error.HTTPError as err:
            resp = err
        try:
            self.send_response(
                getattr(resp, "status", getattr(resp, "code", 500)))
            ctype = resp.headers.get("Content-Type")
            if ctype:
                self.send_header("Content-Type", ctype)
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            reader = getattr(resp, "read1", resp.read)
            while True:
                chunk = reader(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)
                self.wfile.flush()
        finally:
            resp.close()

    # ---------- verbos ----------
    def do_GET(self):
        try:
            self._relay_upstream()
        except Exception as exc:
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: falha GET {self.path}: {exc}")
            self._send_json(502, {"error": f"upstream: {exc}"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            body = json.loads(raw) if raw else {}
        except ValueError:
            body = {}
        # memória: registra antes de repassar (nunca quebra o proxy)
        if self.store is not None and self.sessions is not None:
            try:
                self._record(body)
            except Exception as exc:
                log = get_agent_logger()
                if log:
                    log.warn(f"proxy: falha ao registrar memória: {exc}")
        try:
            self._relay_upstream(raw)
        except Exception as exc:
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: falha ao repassar ao upstream: {exc}")
            self._send_json(502, {"error": f"upstream: {exc}"})

    # ---------- memória ----------
    def _record(self, body: dict) -> None:
        if self.store is None or self.sessions is None:
            return
        sess = self.sessions.touch(body)
        instr = SessionRegistry.first_user_text(body.get("messages"))
        if not instr:
            return
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.store.save_state({
            "objective": instr[:500],
            "source": "cline-proxy",
            "status": "in_progress",
            "started_at": sess.get("first_seen", now),
            "updated_at": now,
            "requests": sess.get("count", 1),
        }, task_id=sess["sid"])
        self.store.append_agent_run({
            "instruction": instr[:500],
            "source": "cline-proxy",
            "run_id": uuid.uuid4().hex[:8],
            "finished": False,
            "attempts": 1,
            "retries": 0,
            "files": [],
            "elapsed_s": None,
            "error": "",
        }, task_id=sess["sid"])
        log = get_agent_logger()
        if log:
            log.info(f"proxy: gravado task_id={sess['sid']} "
                     f"(tasks->{self.store.state.last_backend}, "
                     f"agent_runs->{self.store.agent_runs.last_backend})")