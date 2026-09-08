# ============================================================
#  app/services/proxy/runstate/probe.py — class StreamProbe
#  Analisa o streaming SSE do upstream enquanto é repassado,
#  sem guardar o corpo todo (só extrai o que importa).
# ============================================================

import re


class StreamProbe:
    """Detecta finish_reason e tool_calls no streaming do servidor."""

    _FR_RE = re.compile(r'"finish_reason"\s*:\s*"([a-z_]+)"')
    _TOOL_RE = re.compile(r'"tool_calls"\s*:')

    def __init__(self) -> None:
        self.has_tool_calls = False
        self.finish_reason: str | None = None

    def feed(self, chunk: bytes) -> None:
        if not chunk:
            return
        text = chunk.decode("utf-8", errors="ignore")
        if self._TOOL_RE.search(text):
            self.has_tool_calls = True
        for m in self._FR_RE.finditer(text):
            self.finish_reason = m.group(1)

    def snapshot(self) -> tuple[str, bool]:
        """(finish_reason final, has_tool_calls) para apply_response."""
        return (self.finish_reason or ""), self.has_tool_calls