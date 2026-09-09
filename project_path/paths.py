# ============================================================
#  project_path/paths.py — class ProjectPath
#  Raiz, diretorios e sys.path centralizados (fonte unica).
#  Extraido de project_path/ (regla de oro: archivos >200 linhas
#  se modularizan en pasta com o nome do arquivo).
# ============================================================

import os
import sys


class ProjectPath:
    """Caminhos raiz + sys.path centralizados (fonte unica)."""

    # ROOT = pai desta pasta-package (project_path/paths.py -> ..)
    ROOT: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(ROOT, "data", "json")
    LOG_DIR: str = os.path.join(ROOT, "logs")
    MODELS_DIR: str = os.path.join(ROOT, "models")

    @classmethod
    def ensure(cls) -> None:
        """Garante que a raiz esteja no sys.path (idempotente)."""
        if cls.ROOT not in sys.path:
            sys.path.insert(0, cls.ROOT)

    @classmethod
    def join(cls, *parts: str) -> str:
        """Caminho absoluto dentro do projeto (sem repetir dirname)."""
        return os.path.join(cls.ROOT, *parts)

    @classmethod
    def root(cls) -> str:
        return cls.ROOT