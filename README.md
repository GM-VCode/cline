# 🌙 LunarIA — Servidor LLM Local para o Cline

![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)
![llama.cpp](https://img.shields.io/badge/llama.cpp-Vulkan-DC382D?logo=amd&logoColor=white)
![GPU](https://img.shields.io/badge/GPU-RX_6800-ED1C24?logo=amd&logoColor=white)

> 🤖 Servidor local de LLM (llama.cpp) que expõe uma **API OpenAI-Compatible**
> em `http://127.0.0.1:8080/v1` para o **Cline** (VS Code) usar — com suporte
> a **tool calling** 🔧 e **visão (imagens)** 🖼️ opcional.

---

## 📑 Índice

- [⚡ Como usar (3 passos)](#-como-usar-3-passos)
- [🏗️ Arquitetura](#️-arquitetura)
- [📁 Estrutura do projeto](#-estrutura-do-projeto)
- [⚙️ Configuração (`.env`)](#️-configuração-env)
- [🔌 Configuração do Cline](#-configuração-do-cline)
- [🐍 Ambiente Python (venv)](#-ambiente-python-venv)
- [🎮 llama.cpp (Vulkan)](#-llamacpp-vulkan)
- [🛠️ Problemas comuns](#️-problemas-comuns)

---

## ⚡ Como usar (3 passos)

1. 🖱️ **Duplo clique no atalho `INICIAR-LunarIA`** (raiz) ou `LunarIA-Stack-Completa` (Área de Trabalho)
2. ⏳ Espere aparecer:
   ```
   PRONTO: http://127.0.0.1:8080/v1  (Model ID: LunarIA)
   ```
3. 💬 Abra o **Cline** no VS Code e use normalmente!

> 💡 Se o Cline der erro tipo *"request exceeds the available context size"*,
> o servidor **não está rodando** — inicie pelo atalho.

---

## 🧠 Proxy de memória (opcional — tarefas do Cline no MongoDB)

Do jeito padrão, o Cline fala **direto** com o llama-server e **nada é
registrado** no MongoDB. O proxy fica no meio e grava cada tarefa:

```
Cline (VS Code) → proxy (:8081) → llama-server (:8080)
                        ↓
        MongoDB (cline_agent): tasks + agent_runs
```

### 🗺️ Quem é quem nas portas (são 2 processos separados!)

| Porta | Processo | Como sobe |
|---|---|---|
| `:8080` | **llama-server** (o modelo) | Sobe junto com a stack completa (`INICIAR-LunarIA.bat` / atalho da Área de Trabalho) — roda sem janela, log em `logs\proxy_and_server\llama-server.out.log` |
| `:8081` | **proxy de memória** | Sobe automaticamente com a stack completa (ou sozinho: `python tools\proxy.py`) |

> ⚠️ O bat **não** sobe o proxy — são duas janelas: a do bat (modelo) e a do cmd (proxy).

1. 🖱️ Suba o servidor pelo atalho e **deixe a janela aberta**
2. 🧠 Abra um cmd na pasta do projeto e rode: `python tools\proxy.py`
3. 🔌 No Cline, troque só a **Base URL** para `http://127.0.0.1:8081/v1`
   (API Key e Model ID continuam iguais)
   > 💥 **Falha clássica do teste:** Base URL em `:8080` → o tráfego vai
   > direto ao servidor, o proxy nunca vê nada e **nada é gravado**.

### 📥 Quando grava? Na hora — cada requisição

Não espera a tarefa "concluir": **cada requisição** do Cline é gravada
**antes** de ser repassada ao modelo — 1 doc em `tasks` (com `requests`
incrementando e `status: in_progress`) + 1 doc em `agent_runs` (com
`source: cline-proxy` e a instrução da 1ª mensagem). Sem Mongo ativo,
cai para JSON em `data\json\`.

### ✅ Como conferir se gravou

O proxy grava com `task_id` = **ID da sessão do Cline** (não `current`).
Use o `memory.py` — ele agora lista **todas** as execuções (mais recente
primeiro), independentemente do task_id:

```bash
.venv\Scripts\python.exe data\mongodb\scripts\memory.py agent-runs
.venv\Scripts\python.exe data\mongodb\scripts\memory.py diagnostics
.venv\Scripts\python.exe data\mongodb\scripts\memory.py validations
```

Feche o proxy e volte a Base URL para `http://127.0.0.1:8080/v1` para
voltar ao modo direto (sem registro).

---

## 🏗️ Arquitetura

```
                        ┌─────────────────────────────┐
   suas configs         │     project_path.py         │
  ┌──────────┐  lê     │  class Config               │
  │  .env    ├────────>│  (defaults + .env)          │
  └──────────┘         └──────────────┬──────────────┘
                                      │ fornece
                                      v
                      ┌───────────────────────────────┐                    ┌─────────────────────┐
                      │        app/services/server.py         │    executa         │  llama-server.exe   │
                      │  class LlamaServer            ├───────────────────>│  (C:\llama.cpp)     │
                      │  valida · monta args · roda   │                    └──────────┬──────────┘
                      └───────────────▲───────────────┘                                │
                                      │ LlamaServer(Config()).run()                    v
                              ┌───────┴───────┐                          🖼️ modelo GGUF + mmproj
                              │    main.py    │                                      │
                              │ (só carrega)  │                                      │
                              └───────────────┘                                      │
                                                                                     v
  ┌──────────────┐        API OpenAI-Compatible            ┌────────────────────────────────┐
  │ Cline        │<────────────────────────────────────────┤  http://127.0.0.1:8080/v1      │
  │ (VS Code)    │      🔧 tool calling · 🖼️ visão         └────────────────────────────────┘
  └──────────────┘
```

**Fluxo em palavras:** você configura no `.env` (raiz) → a classe `Config`
(`project_path.py` — fonte única de caminhos + config; `app/config.py` só
re-exporta por compatibilidade) lê o `.env` (o que não estiver lá, usa o
default do `__init__`) → a classe `LlamaServer` (`app/services/server.py`)
valida e inicia o `llama-server.exe` → `main.py` é só o ponto de entrada
central: `LlamaServer(Config()).run()`.

---

## 📁 Estrutura do projeto

```
LunarIA/
│
├── 🚀 main.py                    ← PONTO DE ENTRADA central (só carrega, sem lógica)
├── 🧭 project_path.py            ← FONTE ÚNICA: class ProjectPath (raiz/sys.path)
│                                    + class Config (defaults + leitura do .env)
├── 📦 tools/                     ← ★ ferramentas que rodam separadas do modelo
│   ├── __init__.py
│   ├── validate.py               ← GATE de validação (compileall + unittest + diff)
│   ├── doctor.py                 ← diagnóstico do ambiente (class ModelDoctor)
│   └── logger.py                 ← class AppLogger (logging com níveis → logs/)
├── 📦 app/                       ← código do projeto (pacote Python)
│   ├── __init__.py               ← API pública (Config, LlamaServer, TaskStore)
│   ├── config.py                 ← re-export fino de Config (compatibilidade)
│   ├── task_store.py             ← re-export TaskStore (compatibilidade)
│   └── services/                 ← ★ servicios (cada um com sua classe)
│       ├── __init__.py
│       ├── server.py             ← class LlamaServer: valida, monta args, roda
│       └── task_store.py         ← re-export de data/mongodb
├── 🧪 tests/                     ← testes unitarios (unittest, stdlib)
│   ├── __init__.py
│   ├── test_config.py · test_server.py · test_task_store.py · test_doctor.py
│
├── 📂 logs/                      ← logs centralizados (.log ignorados)
│   ├── app/                     ← níveis (debug/info/warn/error/critical.log)
│   │                               + agent.log (agente) + fallback.log (memória)
│   ├── model/                   ← benchmark.log · executor.log · cline-use.log
│   │                               · corridas <MODELO>_<ts>.log
│   └── proxy_and_server/        ← llama-server.out/err · stack_proxy/server.log
│
├── 🧪 temp/                      ← debug do benchmark/agente (NÃO vai pro git)
│   └── bench_<task_id>/         ← código gerado + _debug_resposta.json +
│                                   _debug_checks.txt (gerado a cada corrida)
│
├── 🖥️ bat/                       ← scripts de inicialização (ver bat/README.md)
│   ├── INICIAR-STACK-COMPLETA.bat     → ⭐ sobe modelo + proxy (1 clique)
│   ├── INICIAR-STACK-COMPLETA.ps1     → lógica do bat acima
│   ├── PARAR-STACK.bat                → derruba tudo
│   └── README.md
│
├── 🧠 models/                    ← modelos .gguf (ver models/README.md)
│   ├── Qwythos-9B-...-Q8_0.gguf        → o modelo principal (~10 GB)
│   └── README.md
│
├── 🖼️ tools/visao/               ← módulo de visão mmproj (ver tools/visao/README.md)
│   ├── Qwythos-9B-...-mmproj-BF16.gguf → projector multimodal (~921 MB)
│   └── README.md
│
├── 🔗 LunarIA-Stack-Completa.lnk  ← ATALHO (Área de Trabalho) — duplo clique aqui!
├── ⚙️ .env                       ← ★ ONDE VOCÊ CONFIGURA TUDO
├── 📋 requirements.txt           ← dependências (só stdlib!)
├── 🧪 validate.py                ← GATE de validação obrigatório (tests + sintaxis + diff)
├── 🧪 tests/                     ← testes unitarios (unittest, stdlib)
├── 🗂️ .clinerules/               ← regras de disciplina do agente (Cline)
│   ├── 01-workflow.md            ← fluxo: auditar → planear → editar → validar → concluir
│   └── 02-task-state.md          ← formato do estado da tarefa (memoria)
├── 📂 data/
│   ├── json/                     ← runtime JSON (fallback): task-state.json, validations.json
│   └── mongodb/                  ← capa de BD (conexión, store, scripts)
│       ├── connection.py         ← class MongoConnection
│       ├── store.py              ← class TaskStore (estado + validações)
│       └── scripts/              ← init_mongo.py · memory.py (CLIs)
├── 🙈 .gitignore
└── 📖 README.md                  ← este guia
```

> 📂 Cada pasta tem seu próprio `README.md` explicando o que guarda e como usar.

---

## 🛠️ Ferramentas (todas via venv, da raiz do projeto)

```bash
# GATE de validação (compileall + unittest + git diff) — OBRIGATÓRIO antes
# de declarar qualquer tarefa concluída; registra cada corrida no Mongo:
.venv\Scripts\python.exe tools\validate.py

# Diagnóstico do ambiente (paths, config, logs, Mongo, API) — grava em
# diagnostics (Mongo) e loga em logs/app/info.log:
.venv\Scripts\python.exe tools\doctor.py

# Benchmark do agente (11 tarefas; verifica de verdade). --real usa o
# modelo no ar (:8080); os debugs ficam em temp\bench_<task_id>\ —
# _debug_resposta.json (todas as respostas do modelo) e _debug_checks.txt:
.venv\Scripts\python.exe tools\benchmarks\run.py --real

# Teste ponta a ponta do agente: 1 tarefa, verificação real, e registro
# em tasks + agent_runs (finished True/False confirmado lendo do banco):
.venv\Scripts\python.exe tools\agent_test.py

# Memória (consulta o Mongo cline_agent; fallback JSON automático):
.venv\Scripts\python.exe data\mongodb\scripts\memory.py state
.venv\Scripts\python.exe data\mongodb\scripts\memory.py agent-runs
.venv\Scripts\python.exe data\mongodb\scripts\memory.py diagnostics
.venv\Scripts\python.exe data\mongodb\scripts\memory.py validations

# Proxy de memória sozinho (default :8081 -> :8080):
.venv\Scripts\python.exe tools\proxy.py
```

Logs: tudo em `logs\` organizado por domínio — `logs\app\` (níveis +
agent.log + fallback.log), `logs\model\` (benchmark/executor/cline-use),
`logs\proxy_and_server\` (llama-server, stack). Quando o MongoDB está
fora do ar, cada fallback ativado fica registrado em `logs\app\fallback.log`.

Relatórios de sessão: `docs\relatorios\` (04 = arquitetura do agente,
05 = loop-guard do proxy, 07 = cobertura de logging, 08 = fase 2).

---

## 🧭 Fluxo disciplinado de trabalho (agente confiável)

Este repo incluye una capa de **disciplina** para que o agente (Cline) trabalhe
sobre ele como um engenheiro cuidadoso, não como um gerador de arquivos. Não
substitue o Cline nem duplica suas ferramentas: **refuerza o SEU comportamento**.

### O que agrega

- **`validate.py`** — um único comando (`python tools/validate.py`) que o agente DEVE
  rodar antes de declarar qualquer tarefa concluida. Roda sintaxis
  (`compileall`), testes unitários (`unittest`) e saneamento do diff
  (`git diff --check`). Exit `0` = pronto; exit `1` = há algo a corrigir.
- **`tests/`** — suite mínima (unittest, **só stdlib**) que trava a interfaz
  atual: leitura do `.env` (`Config`) e montagem/validação de argumentos do
  `LlamaServer`. Sem dependências novas.
- **`.clinerules/`** — regras nativas do Cline que descrevem o ciclo de trabalho:
  auditar → planear em etapas → ler antes de editar → patch pequeno → validar →
  corrigir em loop → revisar diff → só então concluir (mais proibição de
  escopo/seguridade).
- **`.task-state.json`** — memória estruturada da tarefa em curso (objetivo,
  plan com status, arquivos, testes, falhas, decisões).

### Como se usa

1. O agente lê `.clinerules/01-workflow.md` ao começar.
2. Antes de cada edição: audita, planeja e atualiza `.task-state.json`.
3. Depois de cada etapa: `python -m unittest discover -s tests -v`.
4. Antes de concluir: `python tools/validate.py` e revisão do diff.

> ⚙️ Nada disso toca `app/`, `main.py`, `models/`, `tools/visao/`, `bat/` nem
> aumenta o consumo de VRAM. São capas de **control de qualidade** do agente.

---


### 🗄️ Memória persistente (MongoDB local)

O agente guarda o estado da tarefa e o histórico de validações no seu
**MongoDB local** (`mongodb://localhost:27017/`), com fallback automático a JSON.
Toda a lógica de BD vive modularizada em `data/mongodb/`.

- **`data/mongodb/connection.py`** — class `MongoConnection`: conexión/coleções.
- **`data/mongodb/store.py`** — class `TaskStore`: estado + validações (fallback JSON).
- **`data/mongodb/scripts/init_mongo.py`** — cria a base `cline_agent` (coleções
  `tasks`, `validations`) e índices.
- **`data/mongodb/scripts/memory.py`** — CLI para consultar estado e historial.

```bash
.venv\Scripts\python.exe data\mongodb\scripts\init_mongo.py
.venv\Scripts\python.exe data\mongodb\scripts\memory.py state
.venv\Scripts\python.exe data\mongodb\scripts\memory.py validations 10
.venv\Scripts\python.exe data\mongodb\scripts\memory.py conversa <task_id>
```

`memory.py conversa <id>` mostra a **timeline completa** de uma conversa do proxy
(máquina de estados: `in_progress` → `turn_finished` → `completed`/`failed`,
com eventos `user_request`/`model_tool`/`model_final`/`auto_complete`/`user_reopen`).

`validate.py` registra automaticamente cada corrida em `validations`.
Dependência **opcional** (`pymongo`); se não está, tudo segue igual em modo JSON.

---

## ⚙️ Configuração (`.env`)

✏️ Editou o `.env`? **Reinicie o servidor** (feche e rode o atalho de novo).

### 🧠 Modelo

| Variável | Exemplo | O que faz |
|---|:---|---|
| `MODEL_PATH` | `C:\...\models\Qwythos-...-Q8_0.gguf` | Caminho do `.gguf` a carregar |
| `ALIAS` | `LunarIA` | Nome que o Cline vê como **Model ID** |
| `REASONING` | `off` | **Desliga o `<think>`** (default, recomendado p/ Cline) · `on` = liga · `auto` = detecção do llama.cpp. Com thinking ligado, tool calls longos truncam e o Cline degrada |

### 🖼️ Visão (módulo mmproj)

| Variável | O que faz |
|---|---|
| `MM_PROJ_PATH` | Caminho do `*-mmproj-*.gguf` (pasta `tools\visao\`) |
| `MM_PROJ_ENABLED` | **`1` = ativa visão** ✅ · **`0` = modo só texto** 💤 (não carrega o mmproj, economiza VRAM) |
| `IMG_MIN_TOKENS` | Mínimo de tokens por imagem (`1024` recomendado p/ Qwen-VL) |

> 💡 **Modelo sem visão?** `MM_PROJ_ENABLED = 0` — pronto, a pasta `tools\visao\` é ignorada.
> 🔁 **Outro modelo com visão?** O mmproj precisa ser o **daquele** modelo (não é universal).

### 🖧 Rede e hardware

| Variável | Default | O que faz |
|---|:---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8080` | Endereço da API |
| `NGL` | `99` | Camadas na GPU (99 = modelo inteiro na VRAM) 🎮 |
| `CTX` | `409600` | Contexto em tokens (múltiplo de 256) |
| `THREADS` | `12` | Threads de CPU |
| `BATCH` / `UBATCH` | `1024` / `512` | Tamanho de batch |

### 🎲 Sampling

`TEMP`, `TOP_K`, `TOP_P`, `MIN_P`, `REPEAT_PENALTY`, `SEED` — deixe `none` ou
vazio para usar o default do llama.cpp. Recomendado pelo autor do modelo:

```
temp=0.6  ·  top_p=0.95  ·  top_k=20  ·  repeat_penalty=1.05
```

> ⚠️ Quando o Cline envia `temperature` no request, ela **sobrescreve** a `TEMP` do servidor.

---

## 🔌 Configuração do Cline

| Campo | Valor |
|---|---|
| API Provider | `OpenAI Compatible` |
| Base URL | `http://127.0.0.1:8080/v1` |
| API Key | em branco (ou qualquer texto) |
| Model ID | o valor de `ALIAS` no `.env` (ex.: `LunarIA`) |

- 🔧 **Tool calling:** não precisa configurar nada — o Cline envia `tools` no
  request e o llama-server processa (o chat template do GGUF suporta function calling).
- 🖼️ **Visão:** se você ativou a visão **depois** e o Cline "não vê" imagens,
  reinicie o VS Code / re-adicione o provider para ele re-detectar que o modelo
  agora é multimodal (o servidor anuncia `capabilities: [completion, multimodal]`).

---

## 🐍 Ambiente Python (venv)

O projeto usa **só a stdlib** do Python, então não há dependências obrigatórias.
O `.bat` usa o venv automaticamente se existir (senão usa `py -3`).

Para recriar o venv do zero:

```bash
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt
```

> ➕ Se adicionar dependências novas no futuro, liste-as no `requirements.txt`.

---

## 🎮 llama.cpp (Vulkan)

O binário fica em `C:\llama.cpp\llama-server.exe` — build **Vulkan**, que é o
correto para a GPU **AMD Radeon RX 6800** (Vulkan é o backend recomendado para
AMD no Windows; CUDA é só para NVIDIA).

Se um dia precisar reinstalar/atualizar o llama.cpp, **use o build Vulkan**:

1. 📥 Baixe o release mais recente de
   [`github.com/ggml-org/llama.cpp/releases`](https://github.com/ggml-org/llama.cpp/releases)
   escolhendo o pacote `...-bin-win-vulkan-x64.zip`
2. 📂 Extraia em `C:\llama.cpp`
3. ✅ Confira com `llama-server.exe --version` (aparece `ggml-vulkan`)

---

## 🛑 Para parar o servidor

Feche a janela do `.bat` (ou rode):

```bash
taskkill /f /im llama-server.exe
```

---

## 🛠️ Problemas comuns

| 😰 Sintoma | 🔍 Causa / solução |
|---|---|
| `ERROS NA CONFIGURAÇÃO: modelo não encontrado` | `MODEL_PATH` no `.env` aponta para arquivo que não existe |
| Erro de contexto no Cline | Servidor não está rodando — inicie pelo atalho |
| Cline não manda imagens 🖼️ | Reabra o VS Code / re-adicione o provider (cache "text-only") |
| Porta 8080 ocupada | Mude `PORT` no `.env` (e a Base URL no Cline) |
| Proxy não grava nada no Mongo | Base URL do Cline está em `:8080` (tem que ser `:8081`) **ou** o proxy não está rodando — suba `python tools\proxy.py` |
| Modelo degradando (pastas com nomes estranhos, código embaralhado, vários terminais) | thinking (`<think>`) ligado trunca tool calls longos — o default já é `REASONING=off`; se mexeu no `.env`, volte para `off` e reinicie |
| Ver logs detalhados | `logs\proxy_and_server\llama-server.err.log` (e `logs\app\` para os logs do projeto) |
