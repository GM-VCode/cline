# ============================================================
#  project_path/__init__.py — re-export fino (compatibilidade)
#  Antes havia um unico project_path.py (>200 linhas); agora o
#  package project_path/ expone a mesma API publica:
#      from project_path import Config, ProjectPath
# ============================================================

from project_path.config import Config   # noqa: F401
from project_path.paths import ProjectPath  # noqa: F401

__all__ = ["Config", "ProjectPath"]