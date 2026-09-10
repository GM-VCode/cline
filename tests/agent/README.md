# 🤖 `tests\agent\` — Testes do agente (loop, ações, patches)

Cobre o coração do agente: interpretação de ações, aplicação de
patches e composição de contexto.

## Arquivos

| Arquivo | O que testa |
|---|---|
| `test_agent.py` | Loop do agente: orçamento, retries, verificação de saída |
| `test_actions.py` | Ações `write`/`edit`/`run`/`done` (formato, rejeições, execução) |
| `test_agent_context.py` | Composição de contexto/prompt enviado ao modelo |
| `test_patch.py` | `PatchApplier`: aplicação de edits (find/replace) em arquivos |
