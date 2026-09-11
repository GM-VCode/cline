# ============================================================
#  main.py — PONTO DE ENTRADA CENTRAL do servidor local
#
#  Este arquivo NÃO tem lógica nenhuma: só centraliza o load.
#  A lógica está na classe LlamaServer (app/server.py); as
#  configurações, na classe Config (app/config.py), que lê
#  o .env da raiz do projeto.
#
#  Uso:  .venv\Scripts\python.exe main.py
#        (ou pelo atalho LunarIA-Stack-Completa / INICIAR-LunarIA.bat)
# ============================================================

import os
import sys

# Garante que a raiz do projeto esteja no path (p/ importar app.*)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from project_path import Config, ProjectPath  # noqa: E402
ProjectPath.ensure()

from app.services.server import LlamaServer  # noqa: E402


if __name__ == "__main__":
    # stdout redirecionado (hidden/redirect) é cp1252 no Windows:
    # sem isso o emoji do banner derruba o boot com UnicodeEncodeError
    for _s in (sys.stdout, sys.stderr):
        _r = getattr(_s, "reconfigure", None)
        if callable(_r):
            _r(encoding="utf-8", errors="replace")
    print("=" * 62)
    print("  🤖  LunarIA — IA LOCAL ON")
    print(f"  modelo : {Config().ALIAS}")
    print(f"  API    : {Config().BASE_URL}")
    print(f"  logs   : {Config().LOG_DIR}")
    print("=" * 62)
    LlamaServer(Config()).run()
