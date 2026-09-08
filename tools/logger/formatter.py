# ============================================================
#  tools/logger/formatter.py — class LogFormatter
#  Formata a mensagem (%-style + sanitização) e monta a linha
#  padronizada: ts.ms [LEVEL] [name] [PID:x] [T:y] mensagem.
# ============================================================

import os
import threading
import time

from tools.logger.sanitizer import SecretSanitizer


class LogFormatter:
    """Formatação de mensagens e linhas de log (estado por logger)."""

    def __init__(self, name: str) -> None:
        self.name = str(name)

    def message(self, msg: object, args: tuple[object, ...]) -> str:
        """Converte e opcionalmente formata (logger.info('%s', x))."""
        message = str(msg)

        if args:
            try:
                message = message % args
            except (TypeError, ValueError):
                # Formatação incompatível: preserva msg + argumentos.
                message = f"{message} {' '.join(map(str, args))}"

        return SecretSanitizer.sanitize(message)

    def line(self, level: str, message: str) -> str:
        """Linha padronizada com timestamp (ms), PID e thread."""
        now = time.time()
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now))
        milliseconds = int((now % 1) * 1000)
        thread = threading.current_thread()

        return (
            f"{timestamp}.{milliseconds:03d} "
            f"[{level}] "
            f"[{self.name}] "
            f"[PID:{os.getpid()}] "
            f"[T:{thread.name}] "
            f"{message}"
        )
