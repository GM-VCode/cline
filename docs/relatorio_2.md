# relatorio_2 — Centralização de caminhos/config + zerar diagnósticos Pylance

**Data:** 08/09/2026 · **Status:** concluído · **Commit:** NENHUM (a pedido do usuário — tudo no working tree)

---

## 1. Objetivo

Deixar o projeto "top de linha" e uniforme num padrão único:

1. `project_path.py` como **fonte única** de caminhos + configuração (`Config`).
2. Zero sublinhados/diagnósticos do Pylance/Pyright em todo o projeto.
3. Imports limpos e padronizados (sem `sys.path` espalhado em código de biblioteca).
4. `sis.pth` preservado como mecanismo central de resolução de caminhos.
5. `self.cfg` com tipo conhecido; todos os atributos de config explicitamente tipados.

---

## 2. Diagnóstico (causa real dos sublinhados)

O problema **não estava nos atributos** nem no `sis.pth`. Causas combinadas:

| # | Causa | Onde |
|---|---|---|
| 1 | Helpers de config sem anotação (`_get`, `_as_int`, `_as_bool`, `_as_opt`) → atributos inferidos como *partially unknown* | `Config` (antigo `app/config.py`) |
| 2 | `self.cfg = cfg` com parâmetro `cfg=None` → `self.cfg` inferido como `None` → `c.LLAMA_SERVER`, `c.CTX`, `c.LOG_LEVEL` etc. sublinhados | `tools/doctor.py` |
| 3 | Guards mortos `except ImportError: Config = None` → diagnósticos e poluição do padrão | `tools/logger.py`, `app/agent/debug.py`, `tools/doctor.py`, `data/mongodb/store/runtime.py`, `data/mongodb/store/task_store.py` |
| 4 | Erros de tipo legítimos: `raw: bytes = None`, `feedback: str = None`, `response.get(...)` sobre `Optional`, `sys.stdout.reconfigure` (não existe em `TextIO`) | proxy, benchmarks, doctor |
| 5 | Fakes de teste (`SimpleNamespace`, `FakeStore`, params renomeados) incompatíveis com as assinaturas tipadas | `tests/test_agent.py`, `tests/test_patch.py`, `tests/test_server.py`, `tests/test_doctor.py` |

### sis.pth (analisado, NÃO alterado)

- **Local:** `.venv/Lib/site-packages/sis.pth`
- **Conteúdo:** `.` (um ponto)
- **Como funciona:** na inicialização do Python do `.venv`, o `site` processa o `.pth` e adiciona o **diretório de trabalho atual (cwd)** ao `sys.path`. Rodando da raiz do projeto, `import app.*`, `import tools.*`, `import project_path` funcionam.
- **Pylance:** não executa `.pth`; resolve pela raiz do workspace (execution environment default) — por isso os imports nunca foram o problema.
- **Decisão:** **mantido intacto.**

---

## 3. Arquitetura final (padrão único)

```
Python inicia → sis.pth ('.') + ProjectPath.ensure() → sys.path com a raiz
                              │
              ┌───────────────▼────────────────┐
              │  project_path.py (FONTE ÚNICA) │
              │  class ProjectPath (raiz/path) │
              │  class Config (defaults+.env)  │
              └───────────────┬────────────────┘
                              │ import padronizado:
              from project_path import Config, ProjectPath
                              │
        ┌─────────────────────┼──────────────────────────┐
        ▼                     ▼                          ▼
  app/services/server.py  tools/doctor.py          tests/ (Config real nos fakes)
  LlamaServer(self.cfg)   ModelDoctor(self.cfg)

app/config.py = re-export fino → "from app.config import Config" continua funcionando
```

Decisões de estrutura (alinhadas com o usuário):
- **Tudo de `Config` foi para `project_path.py`** (opção escolhida pelo usuário).
- **Atributos de config no `__init__`** (pedido do usuário: "self tudo dentro de init e passar para baixo").
- **`ProjectPath` permanece com constantes de classe** — utilitário sem estado, usado em ~15 arquivos (`ProjectPath.ensure()`, `ProjectPath.ROOT`); converter para instância quebraria tudo sem ganho.

---

## 4. Tipagem da Config (todos explícitos, no `__init__`)

| Atributo | Tipo | Atributo | Tipo |
|---|---|---|---|
| `BASE_DIR` | `str` (=`ProjectPath.ROOT`) | `CTX` | `int` |
| `LOG_DIR/LOG_OUT/LOG_ERR/APP_LOG/AGENT_LOG` | `str` | `TEMP` | `float \| None` |
| `LLAMA_SERVER` | `str` | `TOP_K` | `int \| None` |
| `ALIAS/MODEL_PATH/MM_PROJ_PATH` | `str` | `TOP_P/MIN_P/REPEAT_PENALTY` | `float \| None` |
| `MM_PROJ_ENABLED/KILL_OLD_INSTANCE/SHOW_CONFIG_ON_BOOT` | `bool` | `SEED` | `int \| None` |
| `HOST/LOG_LEVEL` | `str` | `IMG_MIN_TOKENS/NGL/THREADS/BATCH/UBATCH/PORT/WAIT_HEALTH_SECONDS` | `int` |
| `BASE_URL` | property → `str` | | |

- Helpers anotados: `_load_dotenv(path: str) -> dict[str, str]`, `_get(...) -> str`, `_as_int(...) -> int`, `_as_bool(...) -> bool`, `_as_opt(...) -> _T | None` (genérico com `TypeVar`).
- **Zero `Any` · zero `type: ignore` · zero `pyright: ignore` · nada escondido.**

---

## 5. Arquivos alterados (32)

**Núcleo centralização:** `project_path.py` (recebeu `Config` completa — 187 linhas, limite de 200 respeitado), `app/config.py` (re-export fino), `app/__init__.py`, `main.py` (imports padronizados).

**Serviços/agente:** `app/services/server.py` (sys.path removido de biblioteca, `self.cfg: Config`), `app/agent/debug.py`, `checks.py`, `apply.py`, `context.py`, `runner/core.py` (Protocol `TaskStoreProtocol`, `response: dict | None`), `runner/compose.py`, `runner/cycle.py`, `runner/actions.py` — assinaturas anotadas.

**Proxy:** `handler.py` (`raw: bytes | None`, `log_message` com assinatura stdlib), `server.py` (`store` tipado via `TYPE_CHECKING`).

**Tools:** `logger.py` (usa `Config()` direto), `doctor.py` (`ModelDoctor(cfg: Config, store: TaskStore | None = None)`, checks `-> tuple[str, str]`), `benchmarks/executor_llama.py`, `report.py`, `run.py`, `runner.py` (reconfigure via `getattr`, `(response or {}).get`).

**Dados:** `data/mongodb/store/runtime.py` (import direto + `_load_env -> dict[str, str]`), `task_store.py` (import direto de `MongoConnection`), `history.py`/`state.py` (`_coll` com narrowing), `scripts/init_mongo.py` (guarda defensiva).

**Testes:** `test_server.py` e `test_doctor.py` (fakes com `Config()` real), `test_config.py` (`Config()` + `cfg.BASE_URL`), `test_agent.py`/`test_patch.py` (FakeStore conforme o Protocol; params renomeados).

**Docs/estado:** `README.md` (fonte única documentada), `data/json/task-state.json` (memória da tarefa).

---

## 6. Validação (comandos executados e resultado)

| Comando | Resultado |
|---|---|
| `compileall -q app data/mongodb main.py tools tests project_path.py` | OK |
| `unittest discover -s tests` | **Ran 96 tests — OK** |
| `pyright` (1.1.411, instalado na tarefa) em `project_path.py app/ data/mongodb/ tools/ main.py tests/` | **0 errors, 0 warnings, 0 informations** |
| `tools/validate.py` | Sintaxe [OK] · Tests [OK] · git diff --check [OK] |
| `git diff --check` | limpo (só avisos CRLF do Windows) |
| Smoke runtime | `app.config.Config is project_path.Config` → `True`; tipos corretos (CTX lido do `.env`) |

Progressão do Pyright: **19 erros → 2 → 0** (todos corrigidos na causa, nenhum escondido).

---

## 7. Regras respeitadas

- ✅ `sis.pth` NÃO removido nem alterado
- ✅ `.env`, `models/`, `tools/visao/`, `bat/` NÃO tocados
- ✅ Nomes de config preservados (`CTX`, `MODEL_PATH`, `MM_PROJ_PATH`… — nada renomeado)
- ✅ Sem `Any`, sem `type: ignore`, sem desativar diagnósticos
- ✅ Nenhum `git commit` (pedido explícito do usuário)
- ⚠️ `.clinerules/` e `requirements.txt` aparecem modificados por edições **anteriores do usuário** — não foram alterados nesta tarefa

## 8. Como reverter (se necessário)

Como nada foi commitado: `git checkout -- .` reverte os arquivos rastreados; `relatorio_2.md` é novo (não rastreado) e `RELATORIO.md` foi movido para dentro desta pasta.

---

*Gerado pelo agente (Cline) ao concluir a tarefa de uniformização e tipagem do projeto.*

