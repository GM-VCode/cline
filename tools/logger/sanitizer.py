# ============================================================
#  tools/logger/sanitizer.py — class SecretSanitizer
#  Mascara padrões comuns de segredos (password=, token:, ...)
#  antes da mensagem ir para arquivo/console. Conservador:
#  preserva o diagnóstico, esconde só o valor sensível.
# ============================================================


class SecretSanitizer:
    """Sanitização básica e reversível de segredos em mensagens."""

    #: Chaves consideradas sensíveis.
    SENSITIVE_KEYS: tuple[str, ...] = (
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

    #: Máscara aplicada ao valor sensível.
    REDACTED: str = "***REDACTED***"

    @classmethod
    def sanitize(cls, message: str) -> str:
        """Mascara valores após chaves sensíveis (key=value / key: value)."""
        result = message

        for key in cls.SENSITIVE_KEYS:
            lower_result = result.lower()
            start = 0

            while True:
                index = lower_result.find(key, start)
                if index == -1:
                    break

                end_key = index + len(key)
                separator_index = cls._skip_spaces(result, end_key)

                if separator_index < len(result) and result[
                        separator_index] in ("=", ":"):
                    value_start = cls._skip_spaces(result, separator_index + 1)
                    result = cls._redact_value(result, value_start)
                    lower_result = result.lower()
                    start = value_start + len(cls.REDACTED)
                else:
                    start = end_key

        return result

    @staticmethod
    def _skip_spaces(text: str, index: int) -> int:
        """Avança o índice sobre espaços em branco."""
        while index < len(text) and text[index].isspace():
            index += 1
        return index

    @classmethod
    def _redact_value(cls, result: str, value_start: int) -> str:
        """Substitui o valor (com ou sem aspas) pela máscara."""
        quote = None
        if value_start < len(result) and result[value_start] in ('"', "'"):
            quote = result[value_start]
            value_end = result.find(quote, value_start + 1)
            if value_end == -1:
                value_end = len(result)
        else:
            value_end = value_start
            while (value_end < len(result)
                   and not result[value_end].isspace()
                   and result[value_end] not in ",;)"):
                value_end += 1

        return result[:value_start] + cls.REDACTED + result[value_end:]
