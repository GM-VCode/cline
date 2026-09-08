# ============================================================
#  logger.py — class AppLogger
#  Capa de logging centralizada del proyecto. Escribe en
#  logs/app.log (crea logs/ si no existe) y en consola.
#  Soporta niveles: DEBUG < INFO < WARN < ERROR < CRITICAL.
#  El nivel mínimo se toma de .env (LOG_LEVEL) o default INFO.
# ============================================================

import os
import sys
import time

try:
    from app.config import Config
except ImportError:  # pragma: no cover
    Config = None

LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40, "CRITICAL": 50}


class AppLogger:
    """Logger a consola + archivo con timestamps y niveles."""

    def __init__(self, name: str = "app", path: str | None = None,
                 level: str | None = None):
        self.name = name
        self.path = path or self._default_path()
        self.level = (level or self._default_level()).upper()
        if self.level not in LEVELS:
            self.level = "INFO"
        self._ensure_dir()

    def _default_path(self) -> str:
        if Config is not None and hasattr(Config, "APP_LOG"):
            return Config.APP_LOG
        # logger.py -> tools/ -> RAIZ (2 dirname)
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, "logs", "app.log")

    def _default_level(self) -> str:
        if Config is not None and hasattr(Config, "LOG_LEVEL"):
            return str(Config.LOG_LEVEL)
        return "INFO"

    def _ensure_dir(self):
        d = os.path.dirname(self.path) or "."
        os.makedirs(d, exist_ok=True)

    def _enabled(self, level: str) -> bool:
        return LEVELS.get(level.upper(), 20) >= LEVELS[self.level]

    def _line(self, level: str, msg: str) -> str:
        ts = time.strftime("%Y-%m-%dT%H:%M:%S")
        return f"{ts} [{level}] [{self.name}] {msg}"

    def log(self, level: str, msg: str):
        level = level.upper()
        if not self._enabled(level):
            return
        line = self._line(level, msg)
        # arquivo primeiro (nunca depende do encoding do console)
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        try:
            print(line)
        except UnicodeEncodeError:
            # console cp1252/charmap: troca o que não dá para mostrar
            print(line.encode("ascii", "replace").decode("ascii"))

    def debug(self, msg: str):
        self.log("DEBUG", msg)

    def info(self, msg: str):
        self.log("INFO", msg)

    def warn(self, msg: str):
        self.log("WARN", msg)

    def error(self, msg: str):
        self.log("ERROR", msg)

    def critical(self, msg: str):
        self.log("CRITICAL", msg)