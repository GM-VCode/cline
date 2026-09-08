# ============================================================
#  tools/logger/ — pacote de logging (ex-logger.py único)
#
#  Módulos:
#    levels.py     → class LogLevel (níveis + arquivo por nível)
#    sanitizer.py  → class SecretSanitizer (mascara segredos)
#    formatter.py  → class LogFormatter (mensagem + linha)
#    rotator.py    → class LogRotator (rotação por tamanho)
#    writer.py     → class LogWriter (arquivo UTF-8 + console)
#    app_logger.py → class AppLogger (fachada pública)
#
#  API pública preservada:  from tools.logger import AppLogger
# ============================================================

from tools.logger.app_logger import AppLogger
from tools.logger.levels import LEVELS, LogLevel

__all__ = ["AppLogger", "LEVELS", "LogLevel"]
