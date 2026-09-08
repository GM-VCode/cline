# 🏗️ Regras de estrutura de código (padrão top de linha)

1. **Sempre classes** em arquivos Python (nada de scripts soltos com lógica).

1. **Máximo 200 linhas por arquivo.** Passou disso → modularizar.

1. **Arquivo grande → vira pasta com o nome do arquivo**, e tudo dele émodularizado dentro em módulos pequenos, cada um com sua classe.Exemplo: `store.py` grande → `store/` com `runtime.py`, `json_file.py`,`history.py`, `state.py`, `task_store.py` (+ `__init__.py` re-exportando).

1. **Pasta coerente com a função** do código:
  - `app/` → código principal; `app/services/` → serviços.
  - `data/mongodb/` → tudo de banco de dados; `data/mongodb/scripts/` → CLIs do banco.
  - `data/json/` → runtime JSON de fallback.
  - `logs/` → logs centralizados (`.log` ignorados; pasta rastreada com `.gitkeep`).
  - `tests/` → suite unitária.

1. **Nomes inventados jamais**: procurar no projeto antes de criar; preservarinterfaces públicas (re-exports finos mantêm compatibilidade).

1. Git: pastas NUNCA ignoradas; ignorados apenas arquivos de banco/runtimepor nome (`.validations.json`, `data/json/task-state.json`,`data/json/validations.json`, `logs/*.log`).