# 💾 `tests\memoria\` — Testes de persistência (Mongo + fallback JSON)

Cobre a memória do agente: `TaskStore` e recuperação de falhas.
Todos usam paths temporários e URI fechada (não tocam no Mongo real).

## Arquivos

| Arquivo | O que testa |
|---|---|
| `test_task_store.py` | Estado, validações, agent_runs e **benchmarks agrupados por modelo** (1 doc por modelo, timeline de corridas) |
| `test_recovery.py` | Recuperação: falha do Mongo cai para JSON sem quebrar |
