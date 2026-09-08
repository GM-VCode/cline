# ============================================================
#  app/services/proxy/sessions.py — class SessionRegistry
#  Mapeia a conversa do Cline para um task_id: prioriza o
#  session_id do corpo; sem ele, usa a 1.ª mensagem do usuário.
#  Cada toque incrementa o contador da sessão (thread-safe).
# ============================================================

import re
import threading
import time


class SessionRegistry:
    """Registro em memória das sessões de chat ativas no proxy."""

    def __init__(self, clock=None):
        self._lock = threading.Lock()
        self._sessions = {}          # sid -> {first_seen, last_seen, count}
        self._clock = clock or time.time

    # ---------- identificação ----------
    @staticmethod
    def first_user_text(messages) -> str:
        """Texto da 1.ª mensagem do usuário (string ou lista multimodal)."""
        for msg in messages or []:
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                return content
            if isinstance(content, list):
                parts = [p.get("text", "") for p in content
                         if isinstance(p, dict)]
                text = "\n".join(t for t in parts if t)
                if text.strip():
                    return text
        return ""

    @classmethod
    def session_id(cls, body: dict) -> str:
        """ID estável da sessão para o corpo da requisição."""
        sid = body.get("session_id") or body.get("sessionId")
        if sid:
            return str(sid)[:80]
        text = re.sub(r"\s+", " ", cls.first_user_text(
            body.get("messages"))).strip()[:2000]
        if text:
            return "u-" + re.sub(r"[^A-Za-z0-9_-]", "", text[:48])
        return "default"

    # ---------- ciclo de vida ----------
    def touch(self, body: dict) -> dict:
        """Registra/reconhece a sessão e devolve o snapshot dela."""
        sid = self.session_id(body)
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        with self._lock:
            sess = self._sessions.get(sid)
            if sess is None:
                sess = {"sid": sid, "first_seen": now,
                        "last_seen": now, "count": 0}
                self._sessions[sid] = sess
            sess["last_seen"] = now
            sess["count"] += 1
            return dict(sess)

    def summary(self) -> dict:
        with self._lock:
            return {sid: dict(s) for sid, s in self._sessions.items()}
