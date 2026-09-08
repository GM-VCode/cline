# ============================================================
# logger.py — class AppLogger
#
# Camada de logging centralizada do projeto.
# Escreve em logs/app.log e no console.
#
# Recursos:
#   - DEBUG < INFO < WARN < ERROR < CRITICAL
#   - Timestamp com milissegundos
#   - PID e thread
#   - Thread-safe
#   - Rotação automática do arquivo
#   - UTF-8 no arquivo
#   - Compatibilidade com consoles Windows
#   - Sanitização básica de secrets
#   - Suporte opcional a traceback
#   - Formatação com argumentos
#   - Compatibilidade com API existente
#
# Configuração:
#   LOG_LEVEL através de Config().LOG_LEVEL
#   Caminho através de Config().APP_LOG
#
# IMPORTANTE:
#   A API pública existente foi preservada.
# ============================================================

from __future__ import annotations

import os
import sys
import time
import threading
import traceback
from typing import Any

from project_path import Config


LEVELS = {
    "DEBUG": 10,
    "INFO": 20,
    "WARN": 30,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}


class AppLogger:
    """
    Logger centralizado para console + arquivo.

    Compatível com a API anterior:

        logger.debug(...)
        logger.info(...)
        logger.warn(...)
        logger.error(...)
        logger.critical(...)
        logger.log(...)

    O logger é thread-safe e possui rotação automática do arquivo.
    """

    # Limite padrão do arquivo antes da rotação: 10 MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    # Quantidade máxima de arquivos antigos mantidos
    BACKUP_COUNT = 5

    # Lock compartilhado entre todas as instâncias do logger
    _lock = threading.RLock()

    def __init__(
        self,
        name: str = "app",
        path: str | None = None,
        level: str | None = None,
    ):
        self.name = str(name)
        self.path = path or self._default_path()

        configured_level = level or self._default_level()
        self.level = str(configured_level).upper()

        if self.level == "WARNING":
            self.level = "WARN"

        if self.level not in LEVELS:
            self.level = "INFO"

        self._ensure_dir()

    # ========================================================
    # CONFIGURAÇÃO
    # ========================================================

    def _default_path(self) -> str:
        """
        Obtém o caminho padrão através do Config.

        Não altera a origem atual da configuração.
        """
        return Config().APP_LOG

    def _default_level(self) -> str:
        """
        Obtém o nível mínimo através do Config.
        """
        return str(Config().LOG_LEVEL)

    # ========================================================
    # DIRETÓRIOS
    # ========================================================

    def _ensure_dir(self) -> None:
        """
        Garante que o diretório do arquivo de log exista.
        """
        directory = os.path.dirname(os.path.abspath(self.path))

        try:
            os.makedirs(directory, exist_ok=True)
        except OSError:
            # Mantém o comportamento tolerante do logger original.
            pass

    # ========================================================
    # NÍVEL
    # ========================================================

    def _enabled(self, level: str) -> bool:
        """
        Verifica se determinado nível deve ser registrado.
        """
        normalized = str(level).upper()

        if normalized == "WARNING":
            normalized = "WARN"

        current_level = LEVELS.get(self.level, LEVELS["INFO"])
        message_level = LEVELS.get(normalized, LEVELS["INFO"])

        return message_level >= current_level

    # ========================================================
    # SANITIZAÇÃO
    # ========================================================

    @staticmethod
    def _sanitize(message: str) -> str:
        """
        Remove ou mascara padrões comuns de informações sensíveis.

        A sanitização é propositalmente conservadora para não destruir
        informações úteis de diagnóstico.
        """

        sensitive_keys = (
            "password",
            "passwd",
            "pwd",
            "api_key",
            "apikey",
            "secret",
            "token",
            "access_token",
            "refresh_token",
            "authorization",
        )

        result = message

        # Sanitização simples de formatos:
        # password=abc
        # token: abc
        # api_key="abc"
        for key in sensitive_keys:
            lower_result = result.lower()

            start = 0

            while True:
                index = lower_result.find(key, start)

                if index == -1:
                    break

                end_key = index + len(key)

                # Procura "=" ou ":" após a chave
                separator_index = end_key

                while (
                    separator_index < len(result)
                    and result[separator_index].isspace()
                ):
                    separator_index += 1

                if (
                    separator_index < len(result)
                    and result[separator_index] in ("=", ":")
                ):
                    value_start = separator_index + 1

                    while (
                        value_start < len(result)
                        and result[value_start].isspace()
                    ):
                        value_start += 1

                    quote = None

                    if value_start < len(result) and result[value_start] in (
                        '"',
                        "'",
                    ):
                        quote = result[value_start]
                        value_start += 1

                    if quote:
                        value_end = result.find(quote, value_start)

                        if value_end == -1:
                            value_end = len(result)
                    else:
                        value_end = value_start

                        while (
                            value_end < len(result)
                            and not result[value_end].isspace()
                            and result[value_end] not in ",;)"
                        ):
                            value_end += 1

                    result = (
                        result[:value_start]
                        + "***REDACTED***"
                        + result[value_end:]
                    )

                    lower_result = result.lower()
                    start = value_start + len("***REDACTED***")
                else:
                    start = end_key

        return result

    # ========================================================
    # FORMATAÇÃO
    # ========================================================

    def _format_message(
        self,
        msg: Any,
        args: tuple[Any, ...],
    ) -> str:
        """
        Converte e opcionalmente formata a mensagem.

        Permite:

            logger.info("Usuário %s conectado", username)

        sem quebrar chamadas antigas.
        """

        message = str(msg)

        if args:
            try:
                message = message % args
            except (TypeError, ValueError):
                # Caso a formatação não seja compatível, não perde
                # a mensagem original nem os argumentos.
                message = f"{message} {' '.join(map(str, args))}"

        return self._sanitize(message)

    def _line(self, level: str, msg: str) -> str:
        """
        Cria uma linha padronizada de log.
        """

        now = time.time()

        timestamp = time.strftime(
            "%Y-%m-%d %H:%M:%S",
            time.localtime(now),
        )

        milliseconds = int((now % 1) * 1000)

        thread = threading.current_thread()

        return (
            f"{timestamp}.{milliseconds:03d} "
            f"[{level}] "
            f"[{self.name}] "
            f"[PID:{os.getpid()}] "
            f"[T:{thread.name}] "
            f"{msg}"
        )

    # ========================================================
    # ROTAÇÃO
    # ========================================================

    def _rotate_if_needed(self) -> None:
        """
        Faz rotação do arquivo quando ele ultrapassa MAX_FILE_SIZE.
        """

        try:
            if not os.path.exists(self.path):
                return

            if os.path.getsize(self.path) < self.MAX_FILE_SIZE:
                return

            # Remove o backup mais antigo
            oldest = f"{self.path}.{self.BACKUP_COUNT}"

            if os.path.exists(oldest):
                try:
                    os.remove(oldest)
                except OSError:
                    pass

            # Move os backups existentes
            for index in range(self.BACKUP_COUNT - 1, 0, -1):
                source = f"{self.path}.{index}"
                destination = f"{self.path}.{index + 1}"

                if os.path.exists(source):
                    try:
                        os.replace(source, destination)
                    except OSError:
                        pass

            # app.log -> app.log.1
            first_backup = f"{self.path}.1"

            try:
                os.replace(self.path, first_backup)
            except OSError:
                pass

        except OSError:
            # Falha na rotação nunca deve derrubar o projeto.
            pass

    # ========================================================
    # ESCRITA
    # ========================================================

    def _write_file(self, line: str) -> None:
        """
        Escreve uma linha no arquivo com UTF-8.

        O lock evita que múltiplas threads escrevam simultaneamente.
        """

        with self._lock:
            try:
                self._ensure_dir()
                self._rotate_if_needed()

                with open(
                    self.path,
                    "a",
                    encoding="utf-8",
                    errors="replace",
                ) as file:
                    file.write(line + "\n")
                    file.flush()

            except OSError:
                # Logging nunca deve derrubar a aplicação.
                pass

    def _write_console(self, line: str) -> None:
        """
        Escreve no console de maneira segura, inclusive no Windows.
        """

        try:
            print(line, flush=True)

        except UnicodeEncodeError:
            try:
                encoding = getattr(sys.stdout, "encoding", None) or "ascii"

                safe_line = line.encode(
                    encoding,
                    errors="replace",
                ).decode(
                    encoding,
                    errors="replace",
                )

                print(safe_line, flush=True)

            except (OSError, UnicodeError):
                try:
                    print(
                        line.encode("ascii", "replace").decode("ascii"),
                        flush=True,
                    )
                except Exception:
                    pass

        except OSError:
            # Console indisponível não deve interromper a aplicação.
            pass

    # ========================================================
    # LOGGER PRINCIPAL
    # ========================================================

    def log(
        self,
        level: str,
        msg: Any,
        *args: Any,
        exc_info: Any = False,
    ) -> None:
        """
        Registra uma mensagem.

        Compatibilidade:

            logger.log("INFO", "mensagem")

        Também suporta:

            logger.log("ERROR", "Falha: %s", erro)

        E traceback:

            logger.log("ERROR", "Falha", exc_info=True)
        """

        level = str(level).upper()

        if level == "WARNING":
            level = "WARN"

        if level not in LEVELS:
            level = "INFO"

        if not self._enabled(level):
            return

        message = self._format_message(msg, args)

        line = self._line(level, message)

        # Arquivo primeiro.
        self._write_file(line)

        # Depois console.
        self._write_console(line)

        # Traceback, quando solicitado.
        if exc_info:
            try:
                if exc_info is True:
                    traceback_text = traceback.format_exc()
                elif isinstance(exc_info, tuple):
                    traceback_text = "".join(
                        traceback.format_exception(*exc_info)
                    )
                else:
                    traceback_text = str(exc_info)

                traceback_text = self._sanitize(
                    traceback_text.rstrip()
                )

                if traceback_text:
                    for traceback_line in traceback_text.splitlines():
                        self._write_file(traceback_line)
                        self._write_console(traceback_line)

            except Exception:
                # Nunca permitir que o sistema de logging cause
                # uma falha na aplicação.
                pass

    # ========================================================
    # MÉTODOS PÚBLICOS
    # ========================================================

    def debug(self, msg: Any, *args: Any) -> None:
        """Registra mensagem de nível DEBUG."""
        self.log("DEBUG", msg, *args)

    def info(self, msg: Any, *args: Any) -> None:
        """Registra mensagem de nível INFO."""
        self.log("INFO", msg, *args)

    def warn(self, msg: Any, *args: Any) -> None:
        """Registra mensagem de nível WARN."""
        self.log("WARN", msg, *args)

    def warning(self, msg: Any, *args: Any) -> None:
        """Alias compatível para WARN/WARNING."""
        self.log("WARN", msg, *args)

    def error(
        self,
        msg: Any,
        *args: Any,
        exc_info: Any = False,
    ) -> None:
        """Registra mensagem de nível ERROR."""
        self.log(
            "ERROR",
            msg,
            *args,
            exc_info=exc_info,
        )

    def critical(
        self,
        msg: Any,
        *args: Any,
        exc_info: Any = False,
    ) -> None:
        """Registra mensagem de nível CRITICAL."""
        self.log(
            "CRITICAL",
            msg,
            *args,
            exc_info=exc_info,
        )

    def exception(self, msg: Any, *args: Any) -> None:
        """
        Registra ERROR acompanhado do traceback atual.

        Equivalente conceitualmente a:

            logger.error("...", exc_info=True)
        """
        self.log(
            "ERROR",
            msg,
            *args,
            exc_info=True,
        )