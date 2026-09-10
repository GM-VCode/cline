# ============================================================
#  tools/logger/app_logger.py — class AppLogger
#  Fachada pública (mesma API do antigo logger.py único).
#  Filtro por nível mínimo (LOG_LEVEL) + console; no log
#  principal (sem path explícito) cada registro vai somente
#  para o arquivo do seu nível (debug/info/warn/error/critical).
# ============================================================

import os
import traceback
from types import TracebackType
from typing import cast

from project_path import Config
from tools.logger.formatter import LogFormatter
from tools.logger.levels import LogLevel
from tools.logger.rotator import LogRotator
from tools.logger.sanitizer import SecretSanitizer
from tools.logger.writer import LogWriter


class AppLogger:
    """Logger centralizado para console + arquivos (API preservada).

    Comportamento:
      - Nível mínimo configurável (``LOG_LEVEL`` do .env, default INFO).
      - ``split_levels=True`` (automático no path padrão): cada registro
        vai EXCLUSIVAMENTE para o arquivo do seu nível, ao lado do
        path base (debug.log, info.log, warn.log, error.log,
        critical.log).
      - ``path=`` explícito (agent.log, tests): arquivo único.
      - Rotação automática, UTF-8, thread-safe; logging nunca levanta.
    """

    #: Compatibilidade: limites vivem em LogRotator.
    MAX_FILE_SIZE: int = LogRotator.MAX_FILE_SIZE
    BACKUP_COUNT: int = LogRotator.BACKUP_COUNT

    def __init__(self, name: str = "app", path: str | None = None,
                 level: str | None = None,
                 split_levels: bool | None = None) -> None:
        self.name = str(name)
        self.path = path or self._default_path()
        self.level = LogLevel.normalize(level or self._default_level())
        # Split automático só no log principal (sem path explícito).
        self.split_levels = ((path is None) if split_levels is None
                             else bool(split_levels))
        self._formatter = LogFormatter(self.name)
        self._writer = LogWriter()
        self._writer.ensure_dir(self.path)

    # ========================================================
    # CONFIGURAÇÃO
    # ========================================================

    def _default_path(self) -> str:
        """Caminho padrão via Config (fonte única de configuração)."""
        return Config().APP_LOG

    def _default_level(self) -> str:
        """Nível mínimo via Config (LOG_LEVEL do .env)."""
        return str(Config().LOG_LEVEL)

    # ========================================================
    # NÍVEL E DESTINO
    # ========================================================

    def _enabled(self, level: str) -> bool:
        """O nível passa do mínimo configurado?"""
        return LogLevel.value_of(level) >= LogLevel.value_of(self.level)

    def _target_path(self, level: str) -> str:
        """Arquivo destino: exclusivo do nível (split) ou o path base."""
        filename = LogLevel.file_for(level) if self.split_levels else None
        if filename is None:
            return self.path
        directory = os.path.dirname(os.path.abspath(self.path))
        return os.path.join(directory, filename)

    # ========================================================
    # LOGGER PRINCIPAL
    # ========================================================

    def log(self, level: str, msg: object, *args: object,
            exc_info: object = False) -> None:
        """Registra uma mensagem (compatível: log("ERROR", "Falha", ...))."""
        canonical = LogLevel.normalize(level)
        if not self._enabled(canonical):
            return

        message = self._formatter.message(msg, args)
        line = self._formatter.line(canonical, message)
        target = self._target_path(canonical)

        # Arquivo primeiro, depois console.
        self._writer.write_file(line, target)
        self._writer.write_console(line)

        self._write_traceback(exc_info, target)

    def _write_traceback(self, exc_info: object, target: str) -> None:
        """Anexa traceback ao MESMO arquivo do registro, se pedido."""
        if not exc_info:
            return
        try:
            if exc_info is True:
                text = traceback.format_exc()
            elif isinstance(exc_info, tuple):
                info = cast(
                    tuple[type[BaseException] | None, BaseException | None,
                          TracebackType | None],
                    exc_info,
                )
                text = "".join(traceback.format_exception(*info))
            else:
                text = str(exc_info)

            text = SecretSanitizer.sanitize(text.rstrip())
            if text:
                for tb_line in text.splitlines():
                    self._writer.write_file(tb_line, target)
                    self._writer.write_console(tb_line)
        except Exception:
            # Nunca permitir que o logging cause falha na aplicação.
            pass

    # ========================================================
    # MÉTODOS PÚBLICOS
    # ========================================================

    def debug(self, msg: object, *args: object) -> None:
        """Registra mensagem de nível DEBUG."""
        self.log("DEBUG", msg, *args)

    def info(self, msg: object, *args: object) -> None:
        """Registra mensagem de nível INFO."""
        self.log("INFO", msg, *args)

    def warn(self, msg: object, *args: object) -> None:
        """Registra mensagem de nível WARN."""
        self.log("WARN", msg, *args)

    def warning(self, msg: object, *args: object) -> None:
        """Alias compatível para WARN/WARNING."""
        self.log("WARN", msg, *args)

    def error(self, msg: object, *args: object,
              exc_info: object = False) -> None:
        """Registra mensagem de nível ERROR."""
        self.log("ERROR", msg, *args, exc_info=exc_info)

    def critical(self, msg: object, *args: object,
                 exc_info: object = False) -> None:
        """Registra mensagem de nível CRITICAL."""
        self.log("CRITICAL", msg, *args, exc_info=exc_info)

    def exception(self, msg: object, *args: object) -> None:
        """Registra ERROR com o traceback atual."""
        self.log("ERROR", msg, *args, exc_info=True)
