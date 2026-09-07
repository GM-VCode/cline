# 📁 `visao\` — Módulo de Visão (mmproj)

Esta pasta guarda o **multimodal projector** (`*-mmproj-*.gguf`), que é o
"módulo de visão" que dá ao modelo a capacidade de **ver imagens**.

## O que tem aqui

| Arquivo | Tamanho aprox. | Descrição |
|---|---|---|
| `Qwythos-9B-...-mmproj-BF16.gguf` | ~921 MB | Projector multimodal (BF16) correspondente ao modelo Qwythos-9B |

## Como funciona

- O mmproj **não é carregado sozinho** — ele é passado ao llama-server junto
  com o modelo, via flag `-mm` (feito automaticamente pelo `app/server.py`).
- O interruptor liga/desliga é o `MM_PROJ_ENABLED` no `.env` da raiz:
  - `1` → carrega a visão (passa `-mm` + `--image-min-tokens 1024`)
  - `0` → modo só texto (esta pasta é ignorada, economiza VRAM)
- **Cada modelo tem seu próprio mmproj** — se você trocar o modelo em
  `models\`, precisa do mmproj correspondente a ele (não é universal).

## Observação do autor do modelo

O Qwythos-9B é um fine-tune **só de texto**: a visão é herdada do modelo base
(Qwen3.5-VL) e não foi treinada/avaliada pelo autor — funciona, mas sem garantia
de qualidade em tarefas visuais.

> ⚠️ **Nunca comitar esta pasta no git!** Já está no `.gitignore` da raiz.
