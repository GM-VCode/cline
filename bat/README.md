# 📁 `bat\` — Scripts de inicialização

Scripts do Windows para **iniciar/parar a stack** sem digitar comandos.

## Arquivos

| Arquivo | O que faz |
|---|---|
| `INICIAR-STACK-COMPLETA.bat` | ⭐ **O único que você precisa.** Derruba resíduos → sobe o modelo (`main.py`) → espera o health → sobe o proxy (`:8081`) → valida as duas portas. Evita `ECONNREFUSED` no Cline |
| `INICIAR-STACK-COMPLETA.ps1` | Lógica PowerShell chamada pelo `.bat` acima |
| `PARAR-STACK.bat` | Derruba modelo + proxy de uma vez |
| `README.md` | Este guia |

## Atalhos

- **Área de Trabalho:** `LunarIA-Stack-Completa.lnk` — duplo-clique e pronto.
- **Raiz do projeto:** `INICIAR-LunarIA.lnk` (mesmo efeito; o bat real vive nesta pasta).

## Detalhes técnicos

- Os scripts acham a raiz do projeto via `$PSScriptRoot\..` — funcionam de dentro de `bat\`.
- O llama-server roda **sem janela** (por design). Para ver o carregamento: `logs\llama-server.out.log`.
- A configuração **não fica aqui**: edite o `.env` na raiz.
