# ============================================================
#  app/agent/checks.py — class CheckRunner
#  Executa o comando de verificação (ex.: testes) no projeto
#  e devolve (ok, saída). A saída vira feedback para o modelo.
# ============================================================

import subprocess


class CheckRunner:
    """Roda um comando de validação dentro do diretório do projeto."""

    def __init__(self, timeout: int = 120) -> None:
        self.timeout = timeout

    def run(self, check_cmd: list[str], project_dir: str) -> tuple[bool, str]:
        """Retorna (ok: bool, output: str). Nunca lança."""
        try:
            proc = subprocess.run(
                check_cmd, cwd=project_dir,
                capture_output=True, text=True, timeout=self.timeout)
            output = (proc.stdout or "") + (proc.stderr or "")
            cleaned = output.strip()
            if proc.returncode != 0 and not cleaned:
                cleaned = f"check exited with code {proc.returncode}"
            return proc.returncode == 0, cleaned
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            return False, f"erro ao executar check: {exc}"

    def run_shell(self, cmd: str, project_dir: str) -> tuple[bool, str]:
        """Executa comando (string, via shell) — p/ 'run' pedido pelo modelo."""
        try:
            proc = subprocess.run(
                cmd, cwd=project_dir, shell=True,
                capture_output=True, text=True, timeout=self.timeout)
            output = (proc.stdout or "") + (proc.stderr or "")
            cleaned = output.strip()
            if proc.returncode != 0 and not cleaned:
                cleaned = f"run exited with code {proc.returncode}"
            return proc.returncode == 0, cleaned
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            return False, f"erro ao executar run: {exc}"

    @staticmethod
    def feedback_from(instruction: str, output: str,
                      prev_files: dict[str, str] | None = None) -> str:
        """Monta o feedback (2.ª tentativa) a partir da falha."""
        parts = [
            "Sua tentativa anterior não passou na verificação.",
            f"Instrução original: {instruction}",
            f"Saída da verificação:\n{output[:2000]}",
        ]
        if prev_files:
            written = "\n\n".join(
                f"--- {name} ---\n{body[:1500]}"
                for name, body in sorted(prev_files.items()))
            parts.append(
                "O conteúdo que você efetivamente escreveu foi:\n"
                f"{written}\n"
                "IMPORTANTE: a correção precisa estar DENTRO do conteúdo "
                "dos arquivos no JSON (ex.: imports faltando no topo do "
                "arquivo). Dizer que corrigiu na nota não aplica nada.")
        parts.append(
            "Corrija os problemas e reenvie o JSON completo dos arquivos "
            "necessários.")
        return "\n\n".join(parts)
