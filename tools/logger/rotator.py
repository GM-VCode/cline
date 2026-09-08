# ============================================================
#  tools/logger/rotator.py — class LogRotator
#  Rotação automática: path.log > MAX_FILE_SIZE →
#  path.log vira path.log.1 ... path.log.N (o mais antigo sai).
# ============================================================

import os


class LogRotator:
    """Rotação por tamanho, tolerante a falhas (nunca levanta)."""

    #: Limite do arquivo antes de rotacionar: 10 MB.
    MAX_FILE_SIZE: int = 10 * 1024 * 1024

    #: Quantidade máxima de backups antigos mantidos.
    BACKUP_COUNT: int = 5

    def rotate_if_needed(self, path: str) -> None:
        """Rotaciona o arquivo se ele ultrapassou MAX_FILE_SIZE."""
        try:
            if not os.path.exists(path):
                return
            if os.path.getsize(path) < self.MAX_FILE_SIZE:
                return
            self._remove_oldest(path)
            self._shift_backups(path)
            self._promote_current(path)
        except OSError:
            # Falha na rotação nunca deve derrubar o projeto.
            pass

    def _remove_oldest(self, path: str) -> None:
        """Remove o backup mais antigo (path.N)."""
        oldest = f"{path}.{self.BACKUP_COUNT}"
        if os.path.exists(oldest):
            try:
                os.remove(oldest)
            except OSError:
                pass

    def _shift_backups(self, path: str) -> None:
        """Desloca path.1→path.2 ... (abre espaço para o atual)."""
        for index in range(self.BACKUP_COUNT - 1, 0, -1):
            source = f"{path}.{index}"
            destination = f"{path}.{index + 1}"
            if os.path.exists(source):
                try:
                    os.replace(source, destination)
                except OSError:
                    pass

    def _promote_current(self, path: str) -> None:
        """Move o arquivo atual para path.1."""
        try:
            os.replace(path, f"{path}.1")
        except OSError:
            pass
