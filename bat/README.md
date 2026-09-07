# 📁 `bat\` — Scripts de inicialização

Scripts do Windows para **iniciar/parar o servidor** sem digitar comandos.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `INICIAR-Qwythos-9B.bat` | **Principal.** Inicia o servidor com janela de logs visível. Usa o Python do `.venv` se existir (senão `py -3`), chamando o `main.py` da raiz |
| `INICIAR-Qwythos-9B-oculto.bat` | Chama o `.ps1` abaixo (atalho para o PowerShell) |
| `INICIAR-Qwythos-9B-oculto.ps1` | Inicia o servidor em **janela oculta**, grava logs em `server_runner.log` (raiz) e faz health check (`/health`), avisando quando o servidor estiver pronto |
| `README.md` | Este guia |

## Atalho

O arquivo **`INICIAR-Qwythos-9B.lnk`** na **raiz do projeto** é o atalho para
o `INICIAR-Qwythos-9B.bat` desta pasta — é ele que você usa no dia a dia
(dá para copiar para a Área de Trabalho do Windows também).

## Detalhes técnicos

- Os scripts usam `%~dp0..\` / `$PSScriptRoot\..` para achar a **raiz do
  projeto** (onde estão `main.py`, `.venv\` e `.env\`) — por isso funcionam
  mesmo estando dentro de `bat\`.
- Para parar o servidor: feche a janela do `.bat` ou rode
  `taskkill /f /im llama-server.exe`.
- A configuração **não fica aqui**: edite o `.env` na raiz.
