# ============================================================
#  main.py — PONTO DE ENTRADA CENTRAL do servidor local
#
#  Este arquivo NÃO tem lógica nenhuma: só centraliza o load.
#  A lógica está na classe LlamaServer (app/server.py); as
#  configurações, na classe Config (app/config.py), que lê
#  o .env da raiz do projeto.
#
#  Uso:  .venv\Scripts\python.exe main.py
#        (ou pelo atalho INICIAR-Qwythos-9B na raiz)
# ============================================================

import os
import sys

# Garante que a raiz do projeto esteja no path (p/ importar app.*)
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app.server import LlamaServer  # noqa: E402
from app.config import Config       # noqa: E402


if __name__ == "__main__":
    LlamaServer(Config()).run()
