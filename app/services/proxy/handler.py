# ============================================================
#  app/services/proxy/handler.py — class ProxyHandler
#  Recebe o request do Cline, grava a tarefa no Mongo
#  (tasks + agent_runs) e repassa ao llama-server.
#  Streaming SSE sai chunk a chunk (read1 + flush imediato).
# ============================================================

import json
import urllib.error
from http.server import BaseHTTPRequestHandler
from typing import TYPE_CHECKING, Any, cast
from urllib.request import Request, urlopen

from app.agent.debug import get_agent_logger
from app.services.proxy.loopguard import LoopGuard
from app.services.proxy.recorder import ProxyRecorder
from app.services.proxy.runstate import StreamProbe
from app.services.proxy.sessions import SessionRegistry

if TYPE_CHECKING:  # anotação só para o editor (não roda em runtime)
    from app.task_store import TaskStore


class ProxyHandler(BaseHTTPRequestHandler):
    """Handler HTTP: Cline -> Mongo -> llama-server -> Cline."""

    store: "TaskStore | None" = None  # injetado por ProxyServer
    upstream: str = "http://127.0.0.1:8080"
    sessions: SessionRegistry | None = None
    loopguard: LoopGuard | None = None  # injetado por ProxyServer
    SKIP_HEADERS = ("host", "content-length", "connection",
                    "accept-encoding", "transfer-encoding")
    UPSTREAM_TIMEOUT = 600  # geração longa não pode estourar cedo

    # ---------- anti-loop ----------
    def _apply_loopguard(self, body: dict[str, Any], raw: bytes) -> bytes:
        """Detecta request idêntica consecutiva e intervém (fail-open).

        Na 2ª repetição injeta um aviso nas mensagens e sobe a temperature
        para quebrar o determinismo; na 3ª+ o aviso é mais forte. Retorna
        o raw re-serializado ou o original se nada mudar.
        """
        guard = self.loopguard
        if guard is None:
            return raw
        try:
            sid = SessionRegistry.session_id(body)
            rhash = guard.request_hash(body)
            aviso, temp = guard.register(sid, rhash)
            if aviso is None and temp is None:
                return raw
            messages_value = body.get("messages")
            messages: list[Any] = (
                cast(list[Any], messages_value)
                if isinstance(messages_value, list)
                else []
            )
            # Qwen/chat template não aceita system no meio: injeta como user
            messages.append({"role": "user", "content": aviso})
            body["messages"] = messages
            if temp is not None and "temperature" not in body:
                body["temperature"] = temp
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: LOOPGUARD sid={sid[:24]} "
                         f"repeats={guard.repeats_for(sid)} "
                         f"temp={body.get('temperature')}")
            return json.dumps(body, ensure_ascii=False).encode("utf-8")
        except Exception as exc:  # fail-open: nunca bloquear o fluxo
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: loopguard ignorado ({exc})")
            return raw

    # ---------- infra ----------
    def log_message(self, format: str, *args: Any) -> None:
        log = get_agent_logger()
        if log:
            log.debug("proxy: " + (format % args))

    def _send_json(self, code: int, obj: dict[str, Any]) -> None:
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # ---------- relay ----------
    def _relay_upstream(self, raw: bytes | None = None,
                        probe: StreamProbe | None = None) -> None:
        """Repassa ao llama-server e devolve o corpo ao Cline.
        HTTPError (4xx/5xx) é repassado como veio, sem virar 502.
        ``probe`` (opcional) analisa o streaming sem guardar o corpo."""
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
                if probe is not None:
                    try:
                        probe.feed(chunk)
                    except Exception:  # nunca deixa o probe quebrar o fluxo
                        pass
                self.wfile.write(chunk)
                self.wfile.flush()
        finally:
            resp.close()

    # ---------- verbos ----------
    def do_GET(self) -> None:
        try:
            self._relay_upstream()
        except Exception as exc:
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: falha GET {self.path}: {exc}")
            self._send_json(502, {"error": f"upstream: {exc}"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        try:
            parsed: Any = json.loads(raw) if raw else {}
            body = cast(dict[str, Any], parsed) if isinstance(parsed, dict) else {}
        except ValueError:
            body = {}
        recorder = ProxyRecorder(self.store, self.sessions)
        # memória: registra antes de repassar (nunca quebra o proxy)
        if body:
            try:
                recorder.record_request(body)
            except Exception as exc:
                log = get_agent_logger()
                if log:
                    log.warn(f"proxy: falha ao registrar memória: {exc}")
        # anti-loop: request idêntica consecutiva → aviso + temp bump
        if body:
            raw = self._apply_loopguard(body, raw)
        probe = StreamProbe()
        try:
            self._relay_upstream(raw, probe=probe)
            # resposta do modelo: atualiza a máquina de estados (tool/stop)
            if body:
                try:
                    recorder.record_response(body, *probe.snapshot())
                except Exception as exc:
                    log = get_agent_logger()
                    if log:
                        log.warn(f"proxy: falha ao registrar resposta: {exc}")
        except Exception as exc:
            log = get_agent_logger()
            if log:
                log.warn(f"proxy: falha ao repassar ao upstream: {exc}")
            self._send_json(502, {"error": f"upstream: {exc}"})