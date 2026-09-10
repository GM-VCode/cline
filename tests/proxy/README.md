# 🌉 `tests\proxy\` — Testes do proxy de memória

Cobre a ponte Cline → llama-server: sessões, guardas e estado de execução.

## Arquivos

| Arquivo | O que testa |
|---|---|
| `test_proxy_sessions.py` | Sessões: upsert de conversa, timeline (event sourcing), sem duplicatas |
| `test_loopguard.py` | `LoopGuard`: detecção de loop (respostas idênticas repetidas) |
| `test_runstate.py` | `runstate`: estado da execução (run_id, status) |
