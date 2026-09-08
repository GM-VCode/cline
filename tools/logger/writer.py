# ============================================================
#  tools/logger/writer.py — class LogWriter
#  Escrita thread-safe (lock compartilhado entre instâncias):
#  arquivo UTF-8 (com rotação) e console tolerante (Windows).
# ============================================================

import os
import sys
import threading

from tools.logger.rotator import LogRotator


class LogWriter:
    """Escreve linhas em arquivo (UTF-8) e console sem nunca levantar."""

    # Lock compartilhado entre todas as instâncias (comportamento antigo).
    _lock = threading.RLock()

    def __init__(self, rotator: LogRotator | None = None) -> None:
        self.rotator = rotator or LogRotator()

    @staticmethod
    def ensure_dir(path: str) -> None:
        """Garante que o diretório do arquivo exista (tolerante)."""
        directory = os.path.dirname(os.path.abspath(path))
        try:
            os.makedirs(directory, exist_ok=True)
        except OSError:
            pass

    def write_file(self, line: str, path: str) -> None:
        """Acrescenta a linha no arquivo (rotaciona antes se preciso)."""
        with LogWriter._lock:
            try:
                self.ensure_dir(path)
                self.rotator.rotate_if_needed(path)
                with open(path, "a", encoding="utf-8",
                          errors="replace") as file:
                    file.write(line + "\n")
                    file.flush()
            except OSError:
                # Logging nunca deve derrubar a aplicação.
                pass

    def write_console(self, line: str) -> None:
        """Escreve no console com segurança (inclusive Windows/cp1252)."""
        try:
            print(line, flush=True)
        except UnicodeEncodeError:
            self._write_console_safe(line)
        except OSError:
            # Console indisponível não deve interromper a aplicação.
            pass

    @staticmethod
    def _write_console_safe(line: str) -> None:
        """Fallbacks de encoding para consoles limitados."""
        try:
            encoding = getattr(sys.stdout, "encoding", None) or "ascii"
            safe_line = line.encode(encoding, errors="replace").decode(
                encoding, errors="replace")
            print(safe_line, flush=True)
        except (OSError, UnicodeError):
            try:
                print(line.encode("ascii", "replace").decode("ascii"),
                      flush=True)
            except Exception:
                pass
