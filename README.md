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

1. 🖱️ **Duplo clique no atalho `INICIAR-Qwythos-9B`** (na raiz do projeto)
2. ⏳ Espere aparecer:
   ```
   PRONTO: http://127.0.0.1:8080/v1  (Model ID: LunarIA)
   ```
3. 💬 Abra o **Cline** no VS Code e use normalmente!

> 💡 Se o Cline der erro tipo *"request exceeds the available context size"*,
> o servidor **não está rodando** — inicie pelo atalho.

---

## 🏗️ Arquitetura

```
                        ┌─────────────────────────────┐
   suas configs         │      app/config.py          │
  ┌──────────┐  lê     │  class Config               │
  │  .env    ├────────>│  (defaults + .env)          │
  └──────────┘         └──────────────┬──────────────┘
                                      │ fornece
                                      v
                      ┌───────────────────────────────┐                    ┌─────────────────────┐
                      │        app/server.py          │    executa         │  llama-server.exe   │
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
(`app/config.py`) lê o `.env` (o que não estiver lá, usa o default da própria
classe) → a classe `LlamaServer` (`app/server.py`) valida e inicia o
`llama-server.exe` → `main.py` é só o ponto de entrada central:
`LlamaServer(Config()).run()`.

---

## 📁 Estrutura do projeto

```
LunarIA/
│
├── 🚀 main.py                    ← PONTO DE ENTRADA central (só carrega, sem lógica)
├── 📦 app/                       ← código do projeto (pacote Python)
│   ├── __init__.py
│   ├── config.py                 ← class Config: defaults + leitura do .env
│   └── server.py                 ← class LlamaServer: valida, monta args, roda
│
├── 🖥️ bat/                       ← scripts de inicialização (ver bat/README.md)
│   ├── INICIAR-Qwythos-9B.bat          → inicia com janela de logs
│   ├── INICIAR-Qwythos-9B-oculto.bat   → inicia em janela oculta
│   ├── INICIAR-Qwythos-9B-oculto.ps1   → health check automático
│   └── README.md
│
├── 🧠 models/                    ← modelos .gguf (ver models/README.md)
│   ├── Qwythos-9B-...-Q8_0.gguf        → o modelo principal (~10 GB)
│   └── README.md
│
├── 🖼️ visao/                     ← módulo de visão mmproj (ver visao/README.md)
│   ├── Qwythos-9B-...-mmproj-BF16.gguf → projector multimodal (~921 MB)
│   └── README.md
│
├── 🔗 INICIAR-Qwythos-9B.lnk     ← ATALHO na raiz (duplo clique aqui!)
├── ⚙️ .env                       ← ★ ONDE VOCÊ CONFIGURA TUDO
├── 📋 requirements.txt           ← dependências (só stdlib!)
├── 🙈 .gitignore
└── 📖 README.md                  ← este guia
```

> 📂 Cada pasta tem seu próprio `README.md` explicando o que guarda e como usar.

---


## ⚙️ Configuração (`.env`)

✏️ Editou o `.env`? **Reinicie o servidor** (feche e rode o atalho de novo).

### 🧠 Modelo

| Variável | Exemplo | O que faz |
|---|:---|---|
| `MODEL_PATH` | `C:\...\models\Qwythos-...-Q8_0.gguf` | Caminho do `.gguf` a carregar |
| `ALIAS` | `LunarIA` | Nome que o Cline vê como **Model ID** |

### 🖼️ Visão (módulo mmproj)

| Variável | O que faz |
|---|---|
| `MM_PROJ_PATH` | Caminho do `*-mmproj-*.gguf` (pasta `visao\`) |
| `MM_PROJ_ENABLED` | **`1` = ativa visão** ✅ · **`0` = modo só texto** 💤 (não carrega o mmproj, economiza VRAM) |
| `IMG_MIN_TOKENS` | Mínimo de tokens por imagem (`1024` recomendado p/ Qwen-VL) |

> 💡 **Modelo sem visão?** `MM_PROJ_ENABLED = 0` — pronto, a pasta `visao\` é ignorada.
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
| Ver logs detalhados | `C:\llama.cpp\server.err.log` |
