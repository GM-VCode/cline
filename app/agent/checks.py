# ============================================================
#  app/agent/checks.py — class CheckRunner
#  Executa o comando de verificação (ex.: testes) no projeto
#  e devolve (ok, saída). A saída vira feedback para o modelo.
# ============================================================

import subprocess


class CheckRunner:
    """Roda um comando de validação dentro do diretório do projeto."""

    def __init__(self, timeout: int = 120):
        self.timeout = timeout

    def run(self, check_cmd: list, project_dir: str) -> tuple:
        """Retorna (ok: bool, output: str). Nunca lança."""
        try:
            proc = subprocess.run(
                check_cmd, cwd=project_dir,
                capture_output=True, text=True, timeout=self.timeout)
            output = (proc.stdout or "") + (proc.stderr or "")
            return proc.returncode == 0, output.strip()
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            return False, f"erro ao executar check: {exc}"

    @staticmethod
    def feedback_from(instruction: str, output: str) -> str:
        """Monta o feedback (2.ª tentativa) a partir da falha."""
        return (
            "Sua tentativa anterior não passou na verificação.\n"
            f"Instrução original: {instruction}\n"
            f"Saída da verificação:\n{output[:2000]}\n"
            "Corrija os problemas e reenvie o JSON completo dos arquivos "
            "necessários."
        )
