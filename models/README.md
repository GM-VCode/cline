# 📁 `models\` — Modelos GGUF

Esta pasta guarda os **modelos de linguagem** (arquivos `.gguf`) que o
llama-server carrega.

## O que tem aqui

| Arquivo | Tamanho aprox. | Descrição |
|---|---|---|
| `Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-Q8_0.gguf` | ~10 GB | Quantização Q8_0 (8 bits, qualidade quase igual ao FP16) |
| `Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-Q6_K.gguf` | ~7 GB | Quantização Q6_K (6 bits, mais leve / menos VRAM) — **este é o que está ativo no `.env` agora (MODEL_PATH aponta para ele)** |

## Sobre o modelo

- **Base:** Qwen3.5-9B (arquitetura `qwen35`), fine-tune de texto
- **Contexto de treino:** 1M de tokens (o servidor usa 400k por padrão)
- **Fonte:** https://huggingface.co/llmfan46/Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-GGUF
- Suporta **tool calling** nativamente (chat template Qwen)

## Como usar outro modelo

1. Coloque o `.gguf` novo **aqui dentro** (ou em qualquer outra pasta)
2. Edite o `MODEL_PATH` no `.env` da raiz apontando para ele
3. Reinicie o servidor (atalho `INICIAR-Qwythos-9B`)

> ⚠️ **Nunca comitar esta pasta no git!** Os `.gguf` são enormes e já estão
> no `.gitignore` da raiz.
