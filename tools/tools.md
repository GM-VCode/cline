# 🛠️ `tools/` — Ferramentas do Agente Local

Esta carpeta reúne as **ferramentas que rodam separadas do modelo** (regra do
projeto): validación, diagnóstico, logs e benchmark. `main.py` (na raiz) é quem
**sobe o modelo**; estas ferramentas interagem com ele de fora.

> ⚙️ Use sempre o Python da venv: `.venv\Scripts\python.exe`

---

## 📋 Índice

- [1. GATE de validación](#1-gate-de-validación--validatepy)
- [2. Diagnóstico do ambiente (doctor)](#2-diagnóstico-do-ambiente--doctorpy)
- [3. Logger centralizado](#3-logger-centralizado--loggerpy)
- [4. Benchmark do agente](#4-benchmark-do-agente--benchmarks)
- [5. Visão (mmproj)](#5-visão--visao)

---

## 1. GATE de validación — `validate.py`

Comando único que **DEBE** rodar antes de concluir qualquer tarefa de código.
Corre, em ordem, e para na primera falha:

1. **Sintaxis** — `compileall` sobre `app/`, `data/mongodb/`, `main.py`, `tools/`, `tests/`
2. **Testes unitários** — `unittest discover`
3. **Sanity do diff** — `git diff --check`

Registra a corrida en `validations` (Mongo) + `logs/app.log`.

```bash
.venv\Scripts\python.exe .\tools\validate.py
```

**Saída:** `exit 0` = pronto para concluir · `exit 1` = corrigir antes.

---

## 2. Diagnóstico do ambiente — `doctor.py`

Rode **quando notar algo estranho** no modelo/ambiente. Checa:

| Check | O que verifica |
|---|---|
| `paths` | modelo, llama-server.exe, mmproj |
| `config` | CTX múltiplo de 256, LOG_LEVEL válido |
| `logs` | `logs/` gravável |
| `state_json` | JSON de estado legível (detecta corrupção) |
| `mongo` | conexión (warn se cae ao fallback JSON) |
| `memoria` | estado da tarefa na memória |
| `servidor_api` | `/health` responde (warn se apagado, não é falha) |

Resultado `SAUDÁVEL` / `PROBLEMAS ENCONTRADOS`; salva cada corrida em `diagnostics`
(Mongo) ou JSON fallback.

```bash
.venv\Scripts\python.exe .\tools\doctor.py
```

Ver histórico:
```bash
.venv\Scripts\python.exe .\data\mongodb\scripts\memory.py diagnostics
```

---

## 3. Logger centralizado — `logger/` (pacote, ex-`logger.py`)

class **`AppLogger`** (`tools/logger/`): logs com **níveis** + console,
e **arquivo exclusivo por nível** no log principal.

| Nivel | Valor | Arquivo (log principal) |
|---|---|---|
| `DEBUG` | 10 | `logs/debug.log` |
| `INFO` | 20 | `logs/info.log` |
| `WARN` | 30 | `logs/warn.log` |
| `ERROR` | 40 | `logs/error.log` |
| `CRITICAL` | 50 | `logs/critical.log` |

- Log principal (sem `path=` explícito): cada registro vai **somente**
  para o arquivo do seu nível — nada fica mais misturado no `app.log`.
- Com `path=` explícito (`agent.log`, tests): arquivo único como antes.
- Módulos: `levels` (LogLevel) · `sanitizer` (SecretSanitizer) ·
  `formatter` (LogFormatter) · `rotator` (LogRotator) ·
  `writer` (LogWriter) · `app_logger` (AppLogger).

Nível mínimo configurable via `.env` (`LOG_LEVEL`, default `INFO`). Métodos:
`debug()` · `info()` · `warn()` · `error()` · `critical()`.

```python
from tools.logger import AppLogger
log = AppLogger("mi_modulo")   # nível do .env (INFO por default)
log.info("mensaje")            # vai para logs/info.log (+ console)
```

Saída legível do modelo (agente/benchmark): **`logs/saida-modelo.log`** —
via `app/agent/debug.py::get_model_logger` (resposta bruta + interpretação).

---

## 4. Benchmark do agente — `benchmarks/`

Mede **qualidade real do modelo como programador** em 10 tarefas padronizadas
(crear/editar função, bugs, feature com testes, refactor, docs, ...).

```
tools/benchmarks/
├── tasks.py          # class BenchmarkTask + catálogo
├── runner.py         # class ModelExecutor + BenchmarkRunner
├── executor_llama.py # class LlamaExecutor (chama /v1 real)
├── report.py         # class BenchmarkReport (resumo)
└── run.py            # entry point CLI
```

### Executar (valida pipeline, executor local rápido)
```bash
.venv\Scripts\python.exe .\tools\benchmarks\run.py
```
Persiste en Mongo (`benchmark_runs`) ou JSON fallback. ✋ A taxa do executor
local é **fake** (resuelve todo); só valida o pipeline.

### Medir o modelo REAL
```bash
# 1. Suba o servidor primeiro
.venv\Scripts\python.exe .\main.py            # espera "PRONTO http://127.0.0.1:8080/v1"

# 2. Rode uma tarefa com o LlamaExecutor (precisa do modelo no ar)
.venv\Scripts\python.exe -c "from tools.benchmarks.executor_llama import LlamaExecutor; from tools.benchmarks.runner import BenchmarkRunner; from tools.benchmarks.tasks import default_catalog as C; t=[x for x in C() if x.task_id=='003_bug_simples'][0]; print(BenchmarkRunner(LlamaExecutor(),[t]).run_task(t))"
```

Campo `detail` de `LlamaExecutor`: `files_written`, `tokens` reais,
`content_preview`. Para correr **todas** as tarefas, passe `LlamaExecutor()` no
`run.py` (o plugué um flag `--real`).

---

## 5. Visão — `visao/`

`tools/visao/` contém o **mmproj** (`*.-mmproj-*.gguf`) do modelo multimodal.
A visão está **desativada** (`MM_PROJ_ENABLED=0`) para econoizar VRAM. Para
ativar: defina `MM_PROJ_ENABLED=1` no `.env` (e confirme que `MM_PROJ_PATH`
apunta a `tools\visao\...`).

---

## ✅ Checklist rápido

| Quero... | Comando |
|---|---|
| Validar el proyecto antes de concluir | `tools\validate.py` |
| Diagnosticar algo raro | `tools\doctor.py` |
| Empezar el servidor | `main.py` |
| Parar o servidor | `taskkill /f /im llama-server.exe` |
| Benchmark (pipeline) | `tools\benchmarks\run.py` |
| Benchmark (modelo real) | subir servidor + `LlamaExecutor` |
| Ver estado/histórico/server | `data\mongodb\scripts\memory.py` |