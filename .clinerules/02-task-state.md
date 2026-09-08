# 🗂️ Estado estruturado da tarefa

Durante qualquer tarefa de código, o agente mantém uma memória estruturada no arquivo `data/json/task-state.json`. Ela é atualizada no **início de cada etapa** e **ao concluí-la**.

## Formato

```json
{
  "objective": "objetivo atual da tarefa",
  "plan": [
    {
      "id": "step-1",
      "description": "descrição breve",
      "status": "pending | in_progress | completed | blocked",
      "files": ["arquivos que serão modificados"],
      "tests": ["comandos para validá-la"],
      "notes": "notas / resultado"
    }
  ],
  "files_read": ["arquivos lidos"],
  "files_changed": ["arquivos modificados/criados"],
  "tests_run": ["comando → resultado"],
  "known_failures": ["falhas ainda não resolvidas e sua explicação"],
  "decisions": ["decisões importantes e seu motivo"],
  "next_action": "próximo passo concreto"
}
```

## Regras de uso

1. **`files_changed`** deve refletir o que realmente foi alterado no disco (verifique com `git status`), não aquilo que você “pretendia” modificar.

1. **`known_failures`**: se houver um teste falhando ou um erro não resolvido, ele DEVE estar aqui com a explicação e o `next_action`. Não conclua a tarefa com falhas silenciosas.

1. **`tests_run`**: registre o comando e o resultado (por exemplo, `exit 0`, `17 passed`, `1 failed`). Não escreva resultados que não foram executados.

1. Se não for apropriado salvar o arquivo no disco (por exemplo, em uma tarefa efêmera), mantenha a mesma estrutura no contexto da conversa.

1. Ao terminar, este arquivo é considerado uma “prova” do processo: plano → edição → validação → revisão. Não o apague no meio da tarefa.

## Persistência no MongoDB (memória do modelo)

O estado e o histórico das validações também são armazenados no seu **MongoDB local** (com fallback automático para JSON se o Mongo não estiver disponível).

**Banco/coleções:** `cline_agent` → `tasks` (estado) e `validations` (histórico).

**Conexão:** por padrão, `mongodb://localhost:27017/`. É substituída por `MONGODB_URI`, `MONGODB_DB` e `TASK_ID` no `.env` ou nas variáveis de ambiente.

**Uso:**

```bash
.venv\Scripts\python.exe data\mongodb\scripts\init_mongo.py   # cria coleções/índices
.venv\Scripts\python.exe data\mongodb\scripts\memory.py state           # ver estado atual
.venv\Scripts\python.exe data\mongodb\scripts\memory.py validations 20  # histórico
```

`tools/validate.py` registra cada execução em `validations` automaticamente. Os testes de `TaskStore` usam **fallback JSON** com caminhos temporários (não tocam no seu MongoDB).

---

```json
{
  "objective": "Corrigir o bug X em server.py",
  "plan": [
    { "id": "step-1", "description": "reproduzir a falha com um teste",
      "status": "completed", "files": ["tests/test_server.py"], "tests": ["unittest -v"], "notes": "teste com falha reproduziu o bug" },
    { "id": "step-2", "description": "corrigir a causa em server.py",
      "status": "in_progress", "files": ["app/server.py"], "tests": ["unittest -v", "validate.py"], "notes": "" }
  ],
  "files_read": ["app/server.py", "app/config.py"],
  "files_changed": ["tests/test_server.py"],
  "tests_run": ["python -m unittest discover -s tests -v → 1 falha reproduzida"],
  "known_failures": [],
  "decisions": ["Não alterar a assinatura pública de validate()"],
  "next_action": "editar app/server.py e executar validate.py novamente"
}
```