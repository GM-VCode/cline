# ============================================================
#  project_path.py — class ProjectPath
#  Fonte única da raiz do projeto, diretórios relevantes e
#  garantia de sys.path. Os scripts/CLIs delegam aqui em vez de
#  repetir "ROOT = dirname(...)" em cada arquivo.
#
#  Uso:
#    from project_path import ProjectPath
#    ProjectPath.ensure()          # raiz no sys.path (idempotente)
#    ProjectPath.ROOT              # str da raiz
#    ProjectPath.join("logs")      # path absoluto
# ============================================================

import os
import sys


class ProjectPath:
    """Caminhos raiz + sys.path centralizados (fonte única)."""

    ROOT = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(ROOT, "data", "json")
    LOG_DIR = os.path.join(ROOT, "logs")
    MODELS_DIR = os.path.join(ROOT, "models")

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
