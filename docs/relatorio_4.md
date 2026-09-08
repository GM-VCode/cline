# Relatório 4 — Atualizações após o penúltimo commit (`0e67a24`)

**Período:** 2026-09-08 (sessão do dia)
**Commit atual:** `5529158` — *feat: proxy de memoria (1 doc/conversa), separacao agent_runs/tasks, fix upsert created_at, config servidor otimizada (FA/parallel/kv) e MM_PROJ_PATH por nome*
**Escopo do diff:** 36 arquivos, +1723 / −672 linhas

---

## 1. Servidor (llama-server) — `.env` + `app/services/server.py` + `project_path.py`

Eliminação do erro `failed to fit params to free device memory` (VRAM estourada
em 16 GB) e estabilização de tool calls.

| Config | Antes | Agora | Motivo |
|---|---|---|---|
| CTX | 256512 | 100352 | múltiplo de 256; ~100k (3× folga sobre os 27–32k usados) |
| THREADS | 15 | 8 | menos contenção |
| BATCH / UBATCH | 512 | 2048 / 512 | prompt processing mais rápido |
| TEMP / TOP_K / TOP_P | 0.7 / 20 / 0.95 | 0.3 / 40 / 0.9 | sampling determinístico p/ tool calling |
| FLASH_ATTN | — | `on` (`-fa`) | reduz VRAM do KV cache |
| PARALLEL | 4 slots | `--parallel 1` | 1 slot = todo o CTX p/ a conversa |
| KV_CACHE_TYPE | — | `q8_0` (`-ctk/-ctv`) | ~metade da VRAM do cache |

- **`MM_PROJ_PATH` por nome** (`project_path.py::Config._resolve_mmproj`): aceita
  caminho absoluto, nome de arquivo `.gguf` em `models/` ou id base do modelo
  (ex.: `Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic`) — resolve sozinho.
- Novos atributos em `Config` com default seguro: `FLASH_ATTN`, `PARALLEL`,
  `KV_CACHE_TYPE`.
- `server.py::build_args` emite as 3 novas flags (com guarda de validade p/ `-fa`).
- **Resultado em produção:** ~52 t/s estável, boot sem avisos de memória.

## 2. Proxy de memória (Cline → Mongo) — `app/services/proxy/`

Arquitetura: `Cline → :8081 (ProxyRecorder + runstate + SessionRegistry) → :8080`.

- **Novo pacote `runstate/`** (máquina de estados da conversa):
  - `states.py` — `base_doc`, `apply_request`, `apply_response`,
    `promote_timeout`; estados `in_progress → turn_finished → completed/failed`;
    timeline de eventos (event sourcing); `MAX_REQUESTS_LOOP`.
  - `probe.py` — `StreamProbe`.
- **`recorder.py` (novo)** — `ProxyRecorder`: `record_request` / `record_response`;
  1 documento por `task_id` via `upsert_agent_run`; grava também em `tasks`
  (`save_state`) com `source=cline-proxy`.
- **`handler.py`** — integrado ao recorder; separa HTTP puro da memória.
- **`SessionRegistry`** — agrupa requests da mesma conversa no mesmo `task_id`.

### Separação de responsabilidades (fim da duplicação)

| Sistema | Escreve em | Como |
|---|---|---|
| Proxy (`ProxyRecorder`) | `agent_runs` | `upsert` (1 doc/conversa + timeline) |
| `AgentRunner` (CLI) | `tasks` | `save_state` somente (não toca `agent_runs`) |

## 3. Bug crítico corrigido — fallback JSON silencioso

- **Sintoma:** boot dizia "Mongo ATIVO", mas 93 escritas caíram no JSON e 0 no
  Mongo, sem nenhum erro no log.
- **Causa raiz:** `HistoryCollection.upsert` enviava `created_at` no `$set`
  **e** no `$setOnInsert` → conflito rejeitado pelo MongoDB → exceção engolida
  pelo `error_sink`.
- **Fix (`data/mongodb/store/history.py:69-73`):** `created_at` removido do
  `$set` (vai só no `$setOnInsert`).
- **Visibilidade (`recorder.py:77-83`):** se o backend não for `mongo` e houver
  erro, o log imprime `ERRO=...` — nunca mais esconde falha.
- **Regressão:** `test_upsert_doc_com_created_at_nao_falha_no_mongo`
  (`tests/test_task_store.py`) — suíte 14/14 OK.
- **Migração:** `data/mongodb/scripts/migrate_json_runs.py` — 5 conversas do
  fallback JSON migradas para o Mongo.
- **Scripts de apoio** (`data/mongodb/scripts/`): `check_runs.py` (leitura),
  `diag_write.py` (diagnóstico de escrita), `migrate_json_runs.py`.

## 4. Infra / logging

- `tools/logger.py` (553 linhas) → pacote **`tools/logger/`** (regra ≤200
  linhas/arquivo): `levels`, `sanitizer`, `formatter`, `rotator`, `writer`,
  `app_logger` (fachada, API preservada).
- `memory.py` atualizado; `.gitignore` (+1); `models/README.md` revisado.

## 5. Validação

- ✅ Suite completa: 128+ testes passando (incl. novos `test_runstate.py`,
  `test_logger.py`, `test_task_store.py` ampliada, `test_config.py`,
  `test_server.py`, `test_agent.py`).
- ✅ `pyright` 0 erros · `compileall` OK · `tools/validate.py` EXIT 0 ·
  `git diff --check` limpo.
- ✅ Validação ponta a ponta ao vivo: conversa real gravando no Mongo
  (`requests_count` incrementando no mesmo doc, timeline correta, ~52 t/s).

## 6. Pendente (decisão pendente)

1. **Loop Guard no proxy** — detectar requests idênticas consecutivas (hash das
   mensagens por sessão), injetar aviso "divida em comandos menores" e subir a
   temperature (0.3 → 0.7) na repetição. Causa do travamento: determinismo +
   contexto idêntico → resposta idêntica → Cline aborta → loop guard do Cline
   para a task. *Proposto, aguardando aprovação.*
2. **`tools/agent.py:111-112`** — ainda imprime `agent_runs->...` no relatório
   final, mas o runner não escreve mais lá (cosmético).
3. **Gate de sintaxe (`ast.parse`)** antes de aplicar arquivos gerados — foi
   removido no revert e não recolocado; hoje só o `--check` pega SyntaxError.
4. **Coleção `agent_runs`** — tinha 6 docs e passou a mostrar 1; confirmar se
   foi limpeza manual no Compass.
