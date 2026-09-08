# ============================================================
#  tools/logger/levels.py — class LogLevel
#  Catálogo de níveis de log: valor numérico, normalização
#  (WARNING→WARN, inválido→INFO) e arquivo exclusivo de cada
#  nível para o split (debug/info/warn/error/critical .log).
# ============================================================


class LogLevel:
    """Níveis de log canônicos do projeto e seus arquivos."""

    #: Níveis canônicos (nomes usados nas linhas de log).
    CANONICAL: tuple[str, ...] = ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL")

    #: Valor numérico de cada nível (WARNING é alias de WARN).
    VALUES: dict[str, int] = {
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "WARNING": 30,
        "ERROR": 40,
        "CRITICAL": 50,
    }

    #: Arquivo exclusivo de cada nível (split por nível).
    FILES: dict[str, str] = {
        "DEBUG": "debug.log",
        "INFO": "info.log",
        "WARN": "warn.log",
        "ERROR": "error.log",
        "CRITICAL": "critical.log",
    }

    @classmethod
    def normalize(cls, level: str) -> str:
        """Devolve o nome canônico do nível (WARNING→WARN, inválido→INFO)."""
        normalized = str(level).upper()
        if normalized == "WARNING":
            normalized = "WARN"
        if normalized not in cls.CANONICAL:
            return "INFO"
        return normalized

    @classmethod
    def value_of(cls, level: str) -> int:
        """Valor numérico do nível (desconhecido → valor de INFO)."""
        return cls.VALUES.get(level, cls.VALUES["INFO"])

    @classmethod
    def file_for(cls, level: str) -> str | None:
        """Nome do arquivo exclusivo do nível (None → sem split)."""
        return cls.FILES.get(level)


#: Alias de compatibilidade (mesma forma do antigo logger.py).
LEVELS = LogLevel.VALUES
