# ============================================================
#  app/services/proxy/loopguard.py — class LoopGuard
#  Detecta requests idênticas consecutivas por sessão (hash das
#  mensagens) e decide a intervenção anti-loop do proxy:
#    1ª ocorrência → passa normal (None, None)
#    2ª            → nudge ("divida em comandos menores") + temp 0.7
#    3ª+           → aviso forte + temp 0.9
#  Fail-open: nunca levanta; qualquer entrada malformada vira
#  hash estável e não bloqueia o fluxo do proxy.
# ============================================================

import hashlib
import json
import threading

NUDGE_TEMP = 0.7
STRONG_TEMP = 0.9

_NUDGE = (
    "AVISO DO SISTEMA: sua última resposta foi idêntica à anterior e o "
    "comando foi abortado antes de concluir. Mude de estratégia: divida o "
    "trabalho em comandos MENORES, um por vez (no máximo 2-3 encadeados), "
    "e não repita a mesma chamada."
)
_STRONG = (
    "AVISO IMPORTANTE DO SISTEMA: esta é a TERCEIRA vez que você envia a "
    "mesma resposta, e todas foram abortadas. PARE e repense o problema. "
    "Escolha uma abordagem diferente: responda com UM único comando curto "
    "ou explique em texto o que está impedindo o progresso. Não repita a "
    "mesma chamada de novo."
)


class LoopGuard:
    """Circuit breaker anti-loop por sessão, thread-safe.

    O proxy registra o hash das mensagens de cada request antes de
    repassar ao modelo. Hashes idênticos consecutivos na mesma sessão
    indicam loop determinístico (mesma resposta abortada de novo) e
    disparam intervenção progressiva: aviso injetado nas mensagens +
    temperature bump para quebrar o determinismo.
    """

    def __init__(self, clock=None) -> None:
        self._counts: dict[str, int] = {}      # "sid|hash" → repetições
        self._last: dict[str, str] = {}        # sid → último hash
        self._lock = threading.Lock()
        self._clock = clock  # reservado p/ expiração futura de sessões

    # ---------- hash ----------
    def request_hash(self, body: dict) -> str:
        """Hash estável das mensagens (ignora temperature/seed/etc).

        Nunca levanta: body malformado vira hash de sua serialização.
        """
        try:
            messages = body.get("messages") if isinstance(body, dict) else None
            payload = json.dumps(messages, sort_keys=True,
                                 ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            payload = repr(body)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    # ---------- registro/decisão ----------
    def register(self, sid: str, rhash: str) -> tuple[str | None,
                                                      float | None]:
        """Registra a ocorrência e decide (aviso, temperature).

        Returns:
            (None, None)          → sem intervenção
            (aviso, 0.7|0.9)      → injetar aviso e usar a temperature
        """
        key = f"{sid}|{rhash}"
        with self._lock:
            if self._last.get(sid) != rhash:
                self._last[sid] = rhash
                self._counts[key] = 1
                return None, None
            self._counts[key] = self._counts.get(key, 0) + 1
            n = self._counts[key]
            if n == 2:
                return _NUDGE, NUDGE_TEMP
            return _STRONG, STRONG_TEMP

    # ---------- observação (saúde/diagnóstico) ----------
    def repeats_for(self, sid: str) -> int:
        """Repetições consecutivas atuais da sessão (0 se nenhuma)."""
        with self._lock:
            rhash = self._last.get(sid)
            if rhash is None:
                return 0
            return self._counts.get(f"{sid}|{rhash}", 0)
