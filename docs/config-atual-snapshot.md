# 📝 Configurações atuais — Snapshot (08/09/2026)

> **Este arquivo é um backup/documentação do estado ATUAL da configuração**,
> antes de qualquer alteração. Se um dia você quiser voltar para este estado,
> é só copiar os valores daqui para o `.env`.

---

## 🧠 Modelo e identidade

| Variável | Valor atual | Obs |
|---|---|---|
| `MODEL_PATH` | `C:\Users\vinic\Desktop\cline\models\Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-Q6_K.gguf` | Q6_K (~7 GB) — **ativo** |
| `ALIAS` | `LunarIA` | Nome que o Cline vê como "Model ID" |
| Nome do modelo | `Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic` | Base Qwen3.5-9B, fine-tune de texto, tool calling nativo |
| Fonte | https://huggingface.co/llmfan46/Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-GGUF | |

> **Nota do projeto:** existe também o `Q8_0` (~10 GB, qualidade quase igual ao FP16) na
> pasta `models/`, mas **não está ativo** no `.env` no momento.

---

## 👁️ Visão (opcional)

| Variável | Valor atual |
|---|---|
| `MM_PROJ_PATH` | `C:\Users\vinic\Desktop\cline\tools\visao\Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-Q8_0.gguf` |
| `MM_PROJ_ENABLED` | `0` (desativada) |
| `IMG_MIN_TOKENS` | `1024` |

---

## 🌐 Rede

| Variável | Valor atual |
|---|---|
| `HOST` | `127.0.0.1` |
| `PORT` | `8080` |

---

## 🖥️ Hardware / Performance

| Variável | Valor atual | Obs |
|---|---|---|
| `NGL` | `99` | GPU Vulkan RX 6800 (16 GB) |
| `THREADS` | `15` | CPU (16 threads) |
| `CTX` | `256512` | ⚠️ MUITO alto — veja "Observações" |
| `BATCH` | `512` | |
| `UBATCH` | `512` | |

---

## 🎲 Sampling

| Variável | Valor atual |
|---|---|
| `TEMP` | `0.7` |
| `TOP_K` | `20` |
| `TOP_P` | `0.95` |
| `MIN_P` | `0.05` |
| `REPEAT_PENALTY` | `1.05` |
| `SEED` | `-1` |

---

## ⚙️ Comportamento

| Variável | Valor atual |
|---|---|
| `KILL_OLD_INSTANCE` | `1` |
| `WAIT_HEALTH_SECONDS` | `120` |
| `SHOW_CONFIG_ON_BOOT` | `1` |

---

## 💾 Atalho de inicialização

`bat\INICIAR-Qwythos-9B.bat`:
```bat
@echo off
chcp 65001 >nul
title LunarIA (Qwythos-9B) - Servidor para o Cline
if exist "%~dp0..\.venv\Scripts\python.exe" (
  "%~dp0..\.venv\Scripts\python.exe" "%~dp0..\main.py"
) else (
  py -3 "%~dp0..\main.py"
)
pause
```

---

## 🔍 Observações técnicas (contexto do snapshot)

- **Flash attention:** NÃO está explícito no `.env` (build atual: `-fa [on|off|auto]`, default `auto`).
- **Slots paralelos:** o log do boot mostra `n_slots = 4` e `n_ctx_slot = 256512` (padrão do llama-server
  quando não se passa `--parallel`). Ou seja: **4 slots × 256k** de contexto → o KV cache **não cabe**
  nos 16 GB de VRAM sozinho.
- **Aviso real do log:**
  ```
  W common_fit_params: failed to fit params to free device memory:
    n_gpu_layers already set by user to 99, abort
  ```
- **Velocidade medida** em geração: ~**23.5 t/s** nas últimas sessões.
- **Uso real do Cline:** prompts entre **27k e 32k tokens** → o `CTX=256512` atual é **muito maior** que o necessário.
- **`REASONING`:** configurado para **`off`** (desativa o ` thinking`, que degradava o tool calling truncado).

---

*Documentação gerada em 08/09/2026 como snapshot de segurança.*