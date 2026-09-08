# ============================================================
#  app/config.py — RE-EXPORT de Config (compatibilidade)
#  A definição real vive em project_path.py (fonte única de
#  caminhos + settings). Este arquivo fino mantém o import
#  antigo funcionando:
#      from app.config import Config
#  Padrão interno novo:  from project_path import Config
# ============================================================

from project_path import Config  # noqa: F401

__all__ = ["Config"]
