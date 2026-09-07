# LunarIA (Qwythos-9B) — Servidor LLM local para o Cline

Servidor local de LLM (llama.cpp) que expõe uma **API OpenAI-Compatible** em
`http://127.0.0.1:8080/v1` para o Cline (VS Code) usar, com suporte a
**tool calling** e **visão (imagens)** opcional.

---

## Como usar (resumo de 3 passos)

1. Dê **duplo clique em `INICIAR-Qwythos-9B.bat`**
2. Espere aparecer: `PRONTO: http://127.0.0.1:8080/v1 (Model ID: LunarIA)`
3. Abra o **Cline** no VS Code e use normalmente.

> Se o Cline der erro tipo "request exceeds the available context size",
> o servidor **não está rodando** — inicie pelo `.bat`.

---

## Arquitetura (como o projeto funciona)

```
.env  ──le──>  server_config.py  ──fornece──>  server.py  ──executa──>  C:\llama.cpp\llama-server.exe
   (suas configs)      (defaults + .env)      (monta args,                        |
                                              valida, roda)                     v
                                       main.py ──só chama server.main()   modelo GGUF + mmproj
                                                                                 |
Cline (VS Code)  <──── API OpenAI-Compatible ────>  http://127.0.0.1:8080/v1  ───┘
```

**Fluxo:** você configura no `.env` → `server_config.py` lê o `.env` (se uma
variável não existir lá, usa o default) → `server.py` valida e inicia o
`llama-server.exe` → `main.py` é só o ponto de entrada central que chama tudo.

---

## Arquivos do projeto

| Arquivo | O que faz |
|---|---|
| `main.py` | **Ponto de entrada central** (só carrega; sem lógica própria) |
| `server.py` | Lógica: valida config, monta os argumentos e roda o llama-server |
| `server_config.py` | Define os defaults e lê o `.env` (variáveis do `.env` têm prioridade) |
| `.env` | **★ ONDE VOCÊ CONFIGURA TUDO** (modelo, visão, sampling, porta...) |
| `requirements.txt` | Dependências (projeto usa só a stdlib do Python) |
| `.venv/` | Ambiente virtual Python (não comitar) |
| `bat\INICIAR-Qwythos-9B.bat` | **Inicia o servidor** com janela de logs visível |
| `bat\INICIAR-Qwythos-9B-oculto.bat` / `.ps1` | Inicia em janela oculta e testa a saúde |
| `INICIAR-Qwythos-9B.lnk` | **Atalho na raiz** → chama o `.bat` dentro de `bat\` |
| `models/` | Onde fica o modelo `.gguf` |
| `visao/` | Onde fica o módulo de visão `*-mmproj-*.gguf` |
| `README.md` | Este guia |

---

## Configuração pelo `.env`

Editou o `.env`? **Reinicie o servidor** (feche e rode o `.bat` de novo).

### Modelo

| Variável | Exemplo | O que faz |
|---|---|---|
| `MODEL_PATH` | `C:\...\models\Qwythos-...-Q8_0.gguf` | Caminho do `.gguf` a carregar |
| `ALIAS` | `LunarIA` | Nome que o Cline vê como **Model ID** |

### Visão (módulo mmproj)

| Variável | O que faz |
|---|---|
| `MM_PROJ_PATH` | Caminho do `*-mmproj-*.gguf` (pasta `visao\`) |
| `MM_PROJ_ENABLED` | **`1` = ativa visão** · **`0` = modo só texto** (não carrega o mmproj, economiza VRAM) |
| `IMG_MIN_TOKENS` | Mínimo de tokens por imagem (1024 recomendado p/ Qwen-VL) |

Para usar um modelo **sem** visão: `MM_PROJ_ENABLED = 0` — pronto, o `visao\` é ignorado.
Para um **outro** modelo com visão: o mmproj precisa ser o daquele modelo (não é universal).

### Rede e hardware

| Variável | Default | O que faz |
|---|---|---|
| `HOST` / `PORT` | `127.0.0.1` / `8080` | Endereço da API |
| `NGL` | `99` | Camadas na GPU (99 = modelo inteiro na VRAM) |
| `CTX` | `409600` | Contexto em tokens (múltiplo de 256) |
| `THREADS` | `12` | Threads de CPU |
| `BATCH` / `UBATCH` | `1024` / `512` | Tamanho de batch |

### Sampling

`TEMP`, `TOP_K`, `TOP_P`, `MIN_P`, `REPEAT_PENALTY`, `SEED` — deixe `none` ou
vazio para usar o default do llama.cpp. Recomendado pelo autor do modelo:
`temp=0.6, top_p=0.95, top_k=20, repeat_penalty=1.05`.

> Obs.: quando o Cline envia `temperature` no request, ela sobrescreve a `TEMP` do servidor.

---

## Configuração do Cline

| Campo | Valor |
|---|---|
| API Provider | OpenAI Compatible |
| Base URL | `http://127.0.0.1:8080/v1` |
| API Key | em branco (ou qualquer texto) |
| Model ID | o valor de `ALIAS` no `.env` (ex.: `LunarIA`) |

**Tool calling** não precisa configurar nada: o Cline envia `tools` no request
e o llama-server processa (o chat template do GGUF suporta function calling).

**Visão no Cline:** se você ativou a visão depois e o Cline "não vê" imagens,
reinicie o VS Code / re-adicione o provider para ele re-detectar que o modelo
agora é multimodal (o servidor anuncia `capabilities: [completion, multimodal]`).

---

## Ambiente Python (venv)

O projeto usa só a **stdlib** do Python, então não há dependências obrigatórias.
O `.bat` usa o venv automaticamente se existir (senão usa `py -3`).

Para recriar o venv do zero:

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\pip.exe install -r requirements.txt
```

Se adicionar dependências novas no futuro, liste-as no `requirements.txt`.

---

## llama.cpp (Vulkan)

O binário fica em `C:\llama.cpp\llama-server.exe` — build **Vulkan**, que é o
correto para a GPU **AMD Radeon RX 6800** (Vulkan é o backend recomendado para
AMD no Windows; CUDA é só para NVIDIA).

Se um dia precisar reinstalar/atualizar o llama.cpp, **use o build Vulkan**:

1. Baixe o release mais recente de `https://github.com/ggml-org/llama.cpp/releases`
   escolhendo o pacote `...-bin-win-vulkan-x64.zip`
2. Extraia em `C:\llama.cpp`
3. Confira com `llama-server.exe --version` (aparece `ggml-vulkan`)

---

## Para parar o servidor

Feche a janela do `.bat` (ou rode: `taskkill /f /im llama-server.exe`).

## Problemas comuns

| Sintoma | Causa/solução |
|---|---|
| `ERROS NA CONFIGURAÇÃO: modelo não encontrado` | `MODEL_PATH` no `.env` aponta para arquivo que não existe |
| Erro de contexto no Cline | Servidor não está rodando — inicie pelo `.bat` |
| Cline não manda imagens | Reabra o VS Code / re-adicione o provider (cache do tipo "text-only") |
| Porta 8080 ocupada | Mude `PORT` no `.env` (e a Base URL no Cline) |
| Logs detalhados | `C:\llama.cpp\server.err.log` |
