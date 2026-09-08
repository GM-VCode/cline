# 📋 RELATÓRIO — Implementação do Agente Local (LunarIA/Qwythos-9B)

> Histórico completo do que foi implementado para transformar o sistema em
> uma "máquina de código confiável", conforme a prompt inicial.
> **Idioma:** pt-BR (decisão gravada: o usuário fala português, nunca espanhol).

---

## 1. Objetivo

Sair do comportamento `receber tarefa → gerar código → afirmar que terminou`
para um fluxo disciplinado: **auditar → planejar → editar pequeno → validar →
corrigir em loop → revisar diff → concluir só com validação verde**.
Sem duplicar Cline, ferramentas, tool calling ou visão. Zero VRAM extra.

---

## 2. Fase 1 — Disciplina e infraestrutura (concluída)

### Fluxo disciplinado (.clinerules/)
| Arquivo | Função |
|---|---|
| `.clinerules/01-workflow.md` | Ciclo obrigatório: auditar → etapas → ler antes de editar → patch pequeno → validar → loop de correção → revisar diff → proibições de escopo/segurança |
| `.clinerules/02-task-state.md` | Formato do estado estruturado (regla 5 da prompt) + persistência Mongo |

### Gate de validação
- **`validate.py`** — comando único obrigatório antes de concluir qualquer tarefa:
  1. sintaxe (`compileall`) sobre `app/`, `data/mongodb/`, `tests/`, `main.py`, `validate.py`
  2. testes unitários (`unittest discover`)
  3. sanity do diff (`git diff --check`)
  - Registra cada corrida no histórico (Mongo + JSON fallback) e em `logs/app.log`.
  - Exit 0 = pronto; exit 1 = corrigir antes de concluir.

### Memória do agente (MongoDB local)
| Componente | Local | Função |
|---|---|---|
| `MongoConnection` | `data/mongodb/connection.py` | Conexão/ping/coleções (class) |
| `TaskStore` | `data/mongodb/store.py` | Estado da tarefa + histórico de validações, com **fallback automático a JSON** em `data/json/` (class) |
| `MongoInitializer` | `data/mongodb/scripts/init_mongo.py` | Cria base `cline_agent`, coleções `tasks`/`validations`, índices (class) |
| `MemoryCli` | `data/mongodb/scripts/memory.py` | CLI para consultar estado/histórico (class) |

- Connection string: `mongodb://localhost:27017/` (DB `cline_agent`).
- **Com Mongo ativo → só Mongo** (JSON não se cria); sem Mongo → fallback JSON.
- Config opcional via `.env`: `MONGODB_URI`, `MONGODB_DB`, `TASK_ID`.

### Testes
- **22 testes unitários** (unittest, só stdlib) em `tests/`:
  - `test_config.py` — leitura do `.env`, helpers, `BASE_URL`
  - `test_server.py` — `build_args` (flags, sampling, visão) e `validate` (erros)
  - `test_task_store.py` — fallback JSON, roundtrip, validações com limite

### Estrutura de projeto (fina e modular, ≤200 líneas/arquivo)
```
app/
  __init__.py          # API pública: Config, LlamaServer, TaskStore
  config.py            # class Config (incl. LOG_DIR, LOG_LEVEL)
  task_store.py        # re-export compat de TaskStore
  services/
    server.py          # class LlamaServer (com AppLogger)
    task_store.py      # re-export de data/mongodb
data/
  json/                # runtime JSON de fallback (arquivos ignorados por git)
  mongodb/             # capa de BD completa (ver arriba)
logs/                  # logs centralizados (/*.log ignorados, .gitkeep rastreado)
logger.py              # class AppLogger (raiz, junto a main.py)
main.py                # entry point
validate.py            # gate de validação
tests/                 # suite unitária
.clinerules/           # regras de disciplina
```

---

## 3. Fase 2 — Logging com níveis (concluída)

- **`logger.py`** (raiz) — class `AppLogger`:
  - Níveis: `DEBUG < INFO < WARN < ERROR < CRITICAL`.
  - Nível mínimo configurável por `.env` (`LOG_LEVEL`, default `INFO`).
  - Escribe em `logs/app.log` + consola, com timestamps: `ts [LEVEL] [name] msg`.
  - Métodos: `debug/info/warn/error/critical`.
- **`app/config.py`** → `LOG_DIR` (`logs/`), `LOG_OUT`, `LOG_ERR`, `APP_LOG`, `LOG_LEVEL`.
- **`app/services/server.py`** → logs de eventos do ciclo de vida do servidor
  (início, PID, PRONTO, encerramento, falha de health) em nível INFO/ERROR.
- **`validate.py`** → loga resultado com `INFO`/`ERROR`.
- **`.gitignore`** → `logs/*.log` ignorados; `logs/` y `.gitkeep` rastreados.
  `data/` se rastrea completa; ignorados só os archivos de banco por nombre
  (`data/json/task-state.json`, `data/json/validations.json`, `.validations.json`).
  Removido o padrão `_*` que ignoraba por erro `data/mongodb/__init__.py`.

---

## 4. Provas (validações executadas)

| Verificação | Resultado |
|---|---|
| `compileall app data/mongodb tests main.py validate.py logger.py` | ✅ OK |
| `unittest` (suite completa) | ✅ **22 tests OK** |
| `validate.py` | ✅ exit 0 (registra em Mongo + logs/) |
| `git diff --check` | ✅ OK |
| Servidor real: subir → `/health` → `/v1/models` → chat (inferencia 25.8 tok/s) → encerrar | ✅ VRAM liberada |
| `init_mongo.py` / `memory.py` contra Mongo real | ✅ |
| API pública `from app import Config, LlamaServer, TaskStore` | ✅ |
| Logger com níveis (DEBUG filtrado a INFO; ERROR pasa) | ✅ |

### Preservado (nunca tocado)
- `.env` (única mudança: `CTX = 256512`, do usuário), `bat/`, `models/`, `tools/visao/`.
- Interfaces públicas de `Config` e `LlamaServer` sem quebra.

---

## 5. Fase 3 — Ferramenta de diagnóstico (doctor) (concluída)

Ferramenta que você roda quando nota algo estranho no modelo/ambiente:

```bash
python doctor.py
```

- **`doctor.py`** (raiz) — class `ModelDoctor`, 7 checks:
  1. `paths` — modelo, llama-server, mmproj existem
  2. `config` — CTX múltiplo de 256, LOG_LEVEL válido
  3. `logs` — `logs/` gravável
  4. `state_json` — JSON de estado legível (detecta corrupção)
  5. `mongo` — conexão (warn se cair no fallback JSON)
  6. `memoria` — estado da tarefa na memória
  7. `servidor_api` — `/health` responde (warn se desligado, não é falha)
- Resultado: `SAUDÁVEL` (0 falhas) ou `PROBLEMAS ENCONTRADOS`; exit 0/1.
- Salva cada corrida em Mongo (coleção `diagnostics`) ou JSON fallback
  (`data/json/diagnostics.json`); consulta com
  `memory.py diagnostics [N]`.
- Loga em `logs/app.log` com nível INFO/ERROR.
- Stdout reconfigurado para UTF-8 (emojis funcionam em qualquer console Windows).

### Modularização (regra: arquivo >200 linhas → pasta com o nome dele)
`data/mongodb/store.py` (206 linhas) virou **`data/mongodb/store/`**:
| Módulo | Classe | Linhas |
|---|---|---|
| `runtime.py` | `RuntimePaths` — paths + config do runtime | 47 |
| `json_file.py` | `JsonFile` — I/O JSON tolerante | 29 |
| `history.py` | `HistoryCollection` — append/list Mongo+JSON reutilizável | 62 |
| `state.py` | `StateRepo` — estado da tarefa | 49 |
| `task_store.py` | `TaskStore` — fachada pública (mesma API) | 90 |

API pública **intacta**: `from app import TaskStore` e
`from data.mongodb.store import TaskStore` continuam funcionando.
Regra gravada em `.clinerules/03-code-structure.md`.

### Testes: 26 no total
+4 novos: doctor saudável, falha com modelo ausente, diagnóstico no fallback
JSON, filtro de nível no logger.

---

## 6. Fase 4 — Benchmark do agente (concluída)

Medir a qualidade real do modelo como programador em tarefas padronizadas.
Componentes em **`tools/benchmarks/`** (roda separado do modelo, regra do repo):

| Arquivo | Função |
|---|---|
| `tasks.py` | class `BenchmarkTask` + catálogo padronizado (**10 tarefas**: criar/editar função, bugs simples e multi-arquivo, feature com testes, refactor, interpretar erro, projeto desconhecido, código+docs, consertar incompleto) |
| `runner.py` | class `ModelExecutor` (stub injetável) + `BenchmarkRunner` (roda cada tarefa em projeto temporário, mete: terminou?, checks, arquivos, tempo, tool_calls, retries, tokens) |
| `report.py` | class `BenchmarkReport` — resumo (finish_rate, tempo/tool_calls/retries médios) + persistência |
| `run.py` | **entry point CLI**: `python tools/benchmarks/run.py` → roda, resumo y **persiste no Mongo real** (`benchmark_runs`) |

`TaskStore`: coleção `benchmark_runs` + fallback JSON (`data/json/benchmarks.json`).
**Verificado:** execução real salvou `benchmark_runs count: 1` no Mongo.

---

## 7. Estado do projeto (o que falta e o que está concluido)

> ✅ **Infraestrutura operacional: CONCLUIDA**
> - Servidor inicia/encerra, inferência real, API `/v1`, memória Mongo (fallback JSON),
>   gates (`validate.py`), diagnóstico (`doctor.py`), logging por niveles (`logger.py`),
>   benchmark (estrutura), 32 testes, estrutura por capas, docs.
> - Tudo comitado e working tree limpo.

> ✅ **Pendências reais CONCLUÍDAS:**
> 1. **Plugar `ModelExecutor` real** — `LlamaExecutor` plugado via flag `--real`
>    → mede o modelo de verdade! Resultado: **70% (7/10)**.
>    - Fix de codificação (UTF-8 no stdout, report.py/run.py) para rodar no Windows.
> 2. (Opcional) Ajustes de catálogo — mantidos como `iatest/`.
> 📊 **Resultados do benchmark real (Qwythos-9B):**
> - Calibragem (seeds + instruções explícitas): 60% → **80%**
> - **Correção final (`a94c65b`): 100% (10/10 tarefas)**
>   - O Qwythos é modelo de raciocínio (`<think>`): plugar
>     `chat_template_kwargs: {"enable_thinking": false}` + `max_tokens` 2048
>     + strip de `<think>` no parser resolveu as falhas/oscilações.
>   - A 005 (feature com testes, a mais pesada) agora passa: 3/3 checks.
> - Tempo médio: ~1-10s por tarefa; 34 tests OK; validate exit 0
> - `.env` intocado (CTX 256k ≫ prompt + 2048 de saída)
> - Histórico de corridas persistido em `benchmark_runs` (Mongo)

> **Nota honesta:** 100% é do executor real contra o Qwythos-9B local.
> Variabilidade estocástica pode derrubar 1 tarefa numa corrida pontual;
> o retry com feedback (`execute_with_feedback`, com tests) cobre esse caso.

> 🔮 **Melhias opcionais futuras** (não bloqueantes, quando fizer falta):
> - Orçamento de ações (máx. tool_calls/retries por tarefa).

---

## 8. Fase 5 — Testes de recuperação + Agente REAL (concluída)

### 8.1 Testes de recuperação (`tests/test_recovery.py`, 10 tests)
Comprovam a resiliência do store em cenários adversos (nenhum código de
produção precisou mudar — o store já era tolerante, agora isso é **provado**):
- **JSON corrompido** (`task-state.json`, `validations.json`): leitura vira
  valor default (`{}`/`[]`); o próximo `save`/`append` reconstrói o arquivo.
- **Mongo cai no meio da sessão** (simulado com `ConnectionError`):
  `save`/`load`/`append` caem pro JSON automaticamente, sem lançar exceção,
  e registram o erro no `error_sink`.
- **I/O adverso**: `JsonFile.read` corrompido/inexistente → `None`;
  `write` em path inválido → `False` sem lançar.

### 8.2 Decisão de arquitetura: Mongo primário + JSON fallback (por quê)
- **Mongo é o primário**: base `cline_agent` com `tasks` (estado da tarefa),
  `validations` (histórico do validate.py), `diagnostics` (doctor.py) e
  `benchmark_runs` (corridas do benchmark — permite comparar evolução).
- **JSON é o plano B por operação**: se o Mongo estiver caído, a mesma chamada
  grava em `data/json/*.json` sem falhar (testado na 8.1).
- **Por que não SQL no fallback**: os dados são minúsculos (1 doc de estado +
  históricos curtos), sem joins nem queries complexas; JSON (stdlib) cobre isso
  com zero dependência nova. SQL/SQLite só se os históricos crescerem muito —
  e aí a mudança fica contida na camada `JsonFile`/`HistoryCollection`
  (a API `TaskStore` não muda).

### 8.3 Agente real (`app/agent/` + `tools/agent.py`)
O núcleo do agente saiu de dentro do benchmark e virou runtime reutilizável:

| Arquivo | Função |
|---|---|
| `app/agent/checks.py` | class `CheckRunner` — roda comando de verificação (ex.: testes) no projeto; a saída vira feedback do erro |
| `app/agent/runner.py` | class `AgentRunner` — ciclo: modelo → aplica arquivos → verifica → se falhar, reenvia com o **erro real** como feedback (até `max_attempts`) |
| `tools/agent.py` | CLI: `python tools/agent.py --project <dir> --instruction "..." --check "python test_calc.py"` |

Reutiliza a interface `ModelExecutor` (mesma do benchmark) → `LlamaExecutor`
serve aos dois.

**Teste real de ponta a ponta (Qwythos-9B no ar):**
```
$ python tools/agent.py --project tmp/agent_demo \
    --instruction "Corrija add() que subtrai em vez de somar" \
    --check "python test_calc.py"
finalizado: True  tentativas: 1  retries: 0
arquivos: ['calc.py', 'test_calc.py']
verificação: All tests passed!
```
O modelo corrigiu o bug e ainda acrescentou `sub`/`mul`/`div` com proteção
de divisão por zero.

**Validação:** 52 tests OK (44 + 10 recuperação + 8 agente), `validate.py`
exit 0, commits `392375f` … `5cbada3`.

**Limitação honesta:** o modelo escreve arquivos inteiros via JSON e **não vê
o conteúdo atual do projeto** (o prompt não inclui a árvore/conteúdo dos
arquivos). Tarefas em projetos desconhecidos dependem de "adivinhar" a
estrutura a partir da instrução.

---

## 9. PRÓXIMA ETAPA — Contexto do projeto no prompt (visão do código)

> ✅ **CONCLUÍDA** (commit `d17e0f7`) — implementada junto com o prompt de
> identidade (ideia do usuário, para os loops do fire drill).

**Objetivo:** dar ao modelo visão do projeto real antes de editar, acabando com
o "achismo" em projetos desconhecidos (a limitação da 8.3).

### Implementado
| Arquivo | Função |
|---|---|
| `app/agent/context.py` | class `ProjectContext` — árvore + conteúdo dos arquivos no prompt (pula `node_modules`/`.venv`/`.git`/binários; limites: 8 KB/arquivo, 48 KB total, 60 arquivos) |
| `app/agent/identity.md` | **Prompt fixo do agente (editável sem tocar código)**: quem é ele, como trabalha, regras anti-loop ("não invente credenciais/URIs", "se bloqueado, responda `BLOQUEADO: <motivo>`", "não repita tentativa que já falhou do mesmo jeito") |
| `app/agent/identity.py` | class `AgentIdentity` — carrega o `.md` |
| `app/agent/runner.py` | `AgentRunner._compose()`: identidade + contexto + instrução no prompt (flags `--no-context` / `--no-identity` no CLI) |

**Motivação (dados do fire drill):** nos logs do llama-server, similaridade LCP
0.99+ em quase todo request = o modelo re-attemptava a mesma coisa (o caso dos
"logins inventados do Mongo"). É problema de prompt — o `identity.md` instrui a
declarar bloqueio em vez de inventar, e o contexto evita inventar estrutura.

**Teste real de ponta a ponta (Qwythos-9B):** instrução NÃO dizia em qual
arquivo estava o bug — só "há um TODO descrevendo um bug, encontre pelo
contexto". O modelo leu o contexto, achou o TODO em `loja.py`, corrigiu
(`vals[0] / len(vals)` → `sum(vals)`) e o teste passou de primeira.
Antes da etapa 9 isso era impossível (ele teria que adivinhar).

**Validação:** 63 tests OK (52 + 11 novos), `validate.py` exit 0.

**Pendente (opcional):** benchmark A/B `--real` com vs. sem contexto — deixar
para quando o usuário quiser gastar VRAM; a prova de ponta a ponta já cobre o
critério funcional.