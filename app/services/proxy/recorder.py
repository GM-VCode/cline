# ============================================================
#  app/services/proxy/recorder.py — class ProxyRecorder
#  Grava a memória da conversa (tasks + agent_runs) usando a
#  máquina de estados (pacote runstate). Separa a lógica de
#  memória do HTTP puro: o handler só chama record_request e
#  record_response.
# ============================================================

import time
from typing import TYPE_CHECKING, Any

from app.agent.debug import get_agent_logger
from app.services.proxy import runstate
from app.services.proxy.sessions import SessionRegistry

if TYPE_CHECKING:  # anotação só para o editor (sem import circular)
    from app.task_store import TaskStore


class ProxyRecorder:
    """Memória da conversa: 1 documento por task_id + timeline."""

    def __init__(self, store: "TaskStore | None",
                 sessions: SessionRegistry | None,
                 clock: Any = None) -> None:
        self.store = store
        self.sessions = sessions
        self._clock = clock or time.time

    # ---------- request do usuário ----------
    def record_request(self, body: dict[str, Any]) -> None:
        """Request do usuário: reabre/toca a conversa (nunca duplica)."""
        if self.store is None or self.sessions is None:
            return
        instr = SessionRegistry.first_user_text(body.get("messages"))
        if not instr:
            return
        sess = self.sessions.touch(body)
        now = self._clock()
        doc = self.store.get_agent_run(sess["sid"]) or runstate.base_doc(
            sess["sid"], instr, now)
        doc = runstate.apply_request(doc, instr, now)
        self._save(doc, instr, now)

    # ---------- resposta do modelo ----------
    def record_response(self, body: dict[str, Any], finish_reason: str,
                        has_tool_calls: bool) -> None:
        """Resposta do modelo: aplica a transição de estado (tool/stop)."""
        if self.store is None:
            return
        sid = SessionRegistry.session_id(body)
        now = self._clock()
        doc = self.store.get_agent_run(sid)
        if doc is None:
            instr = SessionRegistry.first_user_text(body.get("messages"))
            doc = runstate.base_doc(sid, instr, now)
        doc = runstate.apply_response(doc, finish_reason, has_tool_calls, now)
        self._save(doc, doc.get("instruction", ""), now)

    # ---------- interno ----------
    def _save(self, doc: dict[str, Any], objective: str, now: float) -> None:
        if self.store is None:
            return
        tid = doc["task_id"]
        self.store.upsert_agent_run(doc, task_id=tid)
        self.store.save_state({
            "objective": objective[:500],
            "source": "cline-proxy",
            "status": doc.get("status", runstate.IN_PROGRESS),
            "finished": doc.get("finished", False),
            "requests_count": doc.get("requests_count", 0),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S",
                                        time.localtime(now)),
        }, task_id=tid)
        log = get_agent_logger()
        if log:
            backend = getattr(self.store.agent_runs, "last_backend", "?")
            extra = ""
            if backend != "mongo" and self.store.error:
                extra = f" ERRO={self.store.error}"  # nunca esconder falha
            log.info(f"proxy: task_id={tid} status={doc.get('status')} "
                     f"reqs={doc.get('requests_count')} "
                     f"(agent_runs->{backend}){extra}")