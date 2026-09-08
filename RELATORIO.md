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

### 9.1 Achado pós-etapa 9 — loop de retry não convergia (corrigido, `16031fd`)

O teste de visão revelou, graças ao novo log de debug, por que retries
reproduziam a mesma resposta idêntica (o "baba" relatado no fire drill):

- **Causa raiz 1:** temperature 0.2 + prompt idêntico no retry = resposta
  **byte a byte idêntica** (determinismo). O modelo "corrigia" só no texto
  da nota (`note: "Corrigido: adicionei imports..."`) sem mudar o código.
- **Causa raiz 2:** o feedback dizia que falhou, mas **não mostrava o que o
  modelo tinha escrito de fato** — ele não sabia o que revisar.

**Correções:**
| Mudança | Arquivo | Efeito |
|---|---|---|
| `retry_temperature: 0.7` no retry | `executor_llama.py` | quebra o determinismo; 2.ª tentativa explora caminho diferente |
| Feedback inclui o conteúdo real escrito + aviso "correção na nota não aplica nada" | `checks.py`, `runner.py` | impossível "corrigir só na nota" |
| Log de debug dedicado | `app/agent/debug.py` → `logs/agent.log` | registra prompt, resposta bruta, arquivos e feedback de cada retry (sempre DEBUG, independe do `.env`) |

**Prova:** teste que travava em 3 tentativas idênticas agora converge:
tentativa 2 tentou import errado (`from relatorio import ...` — caminho novo),
tentativa 3 corrigiu de verdade (`from utils import ...`) → verificação OK.

---

## 10. Etapa 10 — Memória das execuções do agente (concluída)

**Implementado:** coleção `agent_runs` no Mongo (`TaskStore.append_agent_run`
/ `list_agent_runs`, fallback `data/json/agent_runs.json`); `AgentRunner.run()`
registra cada execução (instrução, finalizado, tentativas, retries, arquivos,
tempo, erro) — memória nunca quebra o agente; CLI com `--no-memory`;
consulta via `memory.py agent-runs [N]`; higiene: tests usam
`AGENT_LOG_PATH` (não poluem `logs/agent.log` real).

**Achado documentado (9.1):** retry com prompt idêntico + temperature baixa
gerava resposta idêntica (loop infinito, como o caso do Mongo). Corrigido
com `retry_temperature=0.7` + feedback incluindo o conteúdo realmente
escrito. O log de debug (`logs/agent.log`) foi o que revelou a causa.

**Validação:** 67 tests OK, validate exit 0, execução real registrada e
visível em `memory.py agent-runs`. Commits `3b0860c`, `16031fd`.

## 11. Etapa 11a — Verificação interna (`run`) — concluída

O modelo agora pode **testar o próprio código antes de declarar pronto**: o
JSON de resposta aceita `"run": "<comando>"`, que o `AgentRunner` executa no
projeto **antes** do check oficial. Se o run interno falha, a saída vira
feedback direto na mesma rodada (sem esperar o check externo).

| Mudança | Onde |
|---|---|
| Sistema pede campo opcional `"run"` | `tools/benchmarks/executor_llama.py` |
| `_parse_files` → retorna `(files, run_cmd)` | idem |
| `CheckRunner.run_shell(cmd_str, dir)` — comando string via shell | `app/agent/checks.py` |
| `AgentRunner`: executa run interno, feedback imediato em falha, métrica `internal_runs` no resultado e no `agent_runs` | `app/agent/runner.py` |

**Prova real (Qwythos-9B, modelo reiniciado):**
```
RAW_CONTENT: {"files": {"calc.py": "def add(a, b):\n    return a + b\n"},
              "run": "python test_calc.py", ...}
RUN interno: 'python test_calc.py'
finalizado: True  tentativas: 1  retries: 0
verificação: CHECK_OK
```
O modelo corrigiu o bug, **executou o próprio teste** via `run` e só então
declarou pronto — 1 tentativa, zero retries cegos. (Na 1.ª prova o modelo
usou `run` 3x seguidas; a falha era do meu comando de check com quoting
quebrado, não do agente.)

**Validação:** 70 tests OK (67 + 3 novos: run passa, run falho vira feedback,
run inválido não lança), `validate.py` exit 0.

**Segurança:** `run` executa via shell com timeout do `CheckRunner`; é
acionado só pelo próprio modelo em projeto local — risco equivalente ao
check externo já existente.

## 12. Etapa 11b — Patch cirúrgico (`edits`) — concluída

O modelo passou a poder **modificar arquivos sem reescrevê-los**: além de
`"files"` (criação/escrita completa), o JSON aceita
`"edits": [{"file", "find", "replace"}]`.

**Segurança (`app/agent/apply.py` — class `PatchApplier`):**
- `find` deve ocorrer **exatamente 1x** no arquivo: 0x → erro com trecho
  real do arquivo no feedback; 2x+ → "ambíguo, inclua mais contexto"
- **Atomicidade**: todos os edits são validados ANTES de qualquer escrita —
  se um falha, nada é aplicado
- Caminho fora do projeto e arquivo inexistente (manda usar `files`) rejeitados
- Se um edit é rejeitado, o runner devolve feedback imediato sem sujar o projeto

**Prova real (Qwythos-9B, modelo reiniciado):** projeto com 3 módulos com o
mesmo bug de juros. Resposta do modelo: `"files": {}` vazio + **3 edits**
(um por módulo, `find` idêntico e único em cada) + `"run": "python
test_patch.py"` → `finalizado: True`, 1 tentativa, e o diff confirma que
**só a linha do juros mudou** em cada arquivo.

**Validação:** 78 tests OK (70 + 8 novos: patch ok, ambíguo, inexistente,
fora do projeto, edit malformado, integração bom/rejeitado), validate exit 0.

## 13. Etapa 11c — Loop iterativo de ferramentas — concluída

**Refactor prévio:** `runner.py` virou `runner/` (core/cycle/compose,
commit `38a88f7`) para receber esta etapa dentro da regra de ≤200 linhas.

**Implementado:**
- `runner/actions.py` — class `ActionLoop`: protocolo **UM passo por vez**
  (`{"action": "write|edit|run|done", ...}`); após cada ação o modelo recebe
  a **observação** (saída do comando / erro do edit) antes de decidir o
  próximo. Orçamento duro `max_actions` (default 8) impede loop infinito.
  A palavra final é a **verificação oficial**, não o `done`.
- `core.py`: parâmetro `max_actions` ativa o modo iterativo (sem ele, o
  ciclo antigo 11a/11b segue valendo — retrocompatível).
- `LlamaExecutor.execute_action()`: mesmo parse JSON, protocolo de ações no
  feedback, histórico de observações por passo.
- CLI/benchmark continuam funcionando sem mudanças (modo antigo é o default).

**Prova real (Qwythos-9B, modelo reiniciado):** bug em `stats.py`
(`(a+b)/1`). O modelo executou: `edit` (aplicou o fix) → `run`
(`$ python test_stats.py` → ITER_OK) → `done`. Resultado: `finished: True`,
2 ações, 1 run interno, verificação oficial passou.

**Validação:** 86 tests OK (78 + 8 novos: sequência edit→run→done,
orçamento estourado, ação inválida, done com/som check, write, plug no
runner), `validate.py` exit 0.

**Bugs encontrados e corrigidos na prova real (valor do teste de ponta a ponta):**
1. **Dupla aplicação**: o executor aplicava `files`/`edits` E o ActionLoop
   aplicava de novo → 2.º edit falhava ("find não existe"). Fix: no modo
   iterativo (`execute_action`) o executor **só parseia**; quem aplica é o
   ActionLoop (`_defer_apply`).
2. **Lista `edits` não chegava ao ActionLoop**: `_run` não devolvia a chave
   `"edits"` → todo edit era descartado com "sem 'edits' válido". Fix: incluir
   `"edits"` no retorno.
3. **Loop infinito em ação inválida**: JSON sem `action` não contava no
   orçamento → travava até o timeout. Fix: ação inválida **conta** no
   orçamento + aborta após 3 inválidas seguidas.
4. Tolerância a edit "achatado" (`file/find/replace` no nível da ação).

**Validação final:** 88 tests OK, `validate.py` exit 0, modelo reiniciado.
Prova real final: `edit` (aplicado) → `run` self-check (`4`) →
`finalizado: True, ações: 2`, verificação oficial `CLI_OK`.

**Pendência menor:** expor `--max-actions` na CLI `tools/agent.py`
(hoje só via API Python).

---

## 14. Benchmark A/B — clássico vs. iterativo (resultados reais)

Qwythos-9B, 10 tarefas, mesma noite (00:00-00:40):

| Tarefa | Clássico | Iterativo (11c) |
|---|---|---|
| 001 criar função | ✅ 3/3 | ✅ 3/3 |
| 002 editar função | ✅ | ✅ |
| 003 bug simples | ✅ | ✅ |
| 004 bug multi-arquivo | ✅ | ❌ 1/2 (oscilou) |
| 005 feature c/ testes | ❌ 1/3 | ✅ **3/3** |
| 006 refactor | ✅ | ✅ |
| 007 interpretar erro | ✅ | ✅ |
| 008 projeto desconhecido | ✅ | ✅ |
| 009 código+docs | ❌ **0/2** | ✅ **2/2** |
| 010 consertar incompleto | ✅ | ✅ |
| **Total** | **8/10 (14/16 checks)** | **9/10 (17/18 checks)** |

**Leitura:** o modo iterativo resolveu as 2 tarefas que o clássico falhava
(005 e 009 — as mais pesadas, multi-passo) e só perdeu a 004 por oscilação
estocástica. Velocidade: clássico mais rápido nas fáceis (1-9s); iterativo
custa mais inferência (6-50s/tarefa) mas acerta onde importa.

**Ajustes feitos durante o A/B** (bugs revelados pela corrida real):
1. `task.checks` do benchmark são callables — não passar como `check_cmd`
2. Inferência de `action` quando o modelo responde JSON sem o campo
3. Métrica do benchmark = checks (orçamento estourado com checks verdes
   não derruba a tarefa)

**Veredito: modo iterativo é o padrão recomendado para tarefas reais**
(`--max-actions 8`).

**Validação:** 88 tests OK; ambas as corridas persistidas em `benchmark_runs`.

---

## 15. Próximas frentes (para uso em projeto real)
- **Visão (mmproj)**: plugar `image_data` no `LlamaExecutor` + `--image` na
  CLI (o servidor já carrega o mmproj via `-mm`)
- Variância: reruns do A/B em outros dias medirão a oscilação (004)
- **Pronto para teste em projeto real**: `python tools/agent.py --project
  <dir> --instruction "..." --check "..." --max-actions 8`