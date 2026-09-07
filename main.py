# ============================================================
#  main.py — PONTO DE ENTRADA CENTRAL do servidor local
#
#  Este arquivo NÃO tem lógica nenhuma: só centraliza o load.
#  A lógica está em server.py; as configurações, em
#  server_config.py (que lê o .env desta pasta).
#
#  Uso:  .venv\Scripts\python.exe main.py
#        (ou simplesmente rode INICIAR-Qwythos-9B.bat)
# ============================================================

import os
import sys

# Garante que os imports (server, server_config) sejam encontrados
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import server  # noqa: E402  (lógica de inicialização do llama-server)


if __name__ == "__main__":
    server.main()
