# 🧪 `tests\chat_test\` — Testes de modelo de CHAT (uso de ferramentas)

Avalia **como o modelo de chat se comporta como agente** (estilo Cline):
responde JSON? Usa `write` certo? Conserta bugs sem quebrar testes?

## Arquivos

| Arquivo | O que testa |
|---|---|
| `test_cline_use.py` | Valida o `Grader` de `tools\cline_use\`: checks de escrita, sintaxe, re-export no `__init__`, tipagem, teste intacto (armadilha) e comando de verificação real |

## Relacionado

- O bench que **executa** essas tarefas contra o modelo real: `tools\cline_use\run.py`
  (logs por corrida em `logs\model\<MODELO>_<timestamp>.log`)
- Está aqui e não em `benchmarks\` porque avalia **modelos de chat genéricos**
  (Qwythos local, Copilot, etc.) — diferente do benchmark de tarefas do projeto.
