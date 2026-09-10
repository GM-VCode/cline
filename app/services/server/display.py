class ServerDisplay:
    """Formata a configuração efetiva para a saída da CLI."""

    @staticmethod
    def show(args: list[str]) -> None:
        print("=" * 60)
        print("  Qwythos-9B — config efetiva")
        print("=" * 60)
        for flag, value in ServerDisplay._pair_args(args):
            print(f"  {flag}" if value is None else f"  {flag:<16} {value}")
        print("=" * 60)

    @staticmethod
    def _pair_args(args: list[str]) -> list[tuple[str, str | None]]:
        pairs: list[tuple[str, str | None]] = []
        index = 0
        while index < len(args):
            if index + 1 < len(args) and ServerDisplay._is_value(args[index + 1]):
                pairs.append((args[index], args[index + 1]))
                index += 2
            else:
                pairs.append((args[index], None))
                index += 1
        return pairs

    @staticmethod
    def _is_value(token: str) -> bool:
        if not token.startswith("-"):
            return True
        rest = token[1:].replace(".", "").replace(",", "").lstrip("-")
        return rest.isdigit()
