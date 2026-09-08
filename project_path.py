# ============================================================
#  project_path.py — class ProjectPath
#  Fonte única da raiz do projeto e do sys.path. Scripts que
#  rodam de subpastas ainda precisam do bootstrap mínimo
#  (sys.path.insert do diretório pai) para importar este módulo;
#  todo o resto usa ProjectPath.ROOT / ProjectPath.ensure().
# ============================================================

import os
import sys


class ProjectPath:
    """Raiz do projeto e garantia de sys.path centralizada."""

    ROOT = os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def ensure(cls) -> None:
        """Garante que a raiz esteja no sys.path (idempotente)."""
        if cls.ROOT not in sys.path:
            sys.path.insert(0, cls.ROOT)

    @classmethod
    def root(cls) -> str:
        return cls.ROOT
