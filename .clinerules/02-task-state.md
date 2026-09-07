# 🗂️ Estado estructurado da tarefa

Durante qualquer tarefa de código, o agente mantiene memória estruturada no
arquivo `data/json/task-state.json`. Se atualiza ao **inicio de cada etapa** e
**al concluí-la**.

## Formato

```json
{
  "objective": "objetivo actual de la tarea",
  "plan": [
    {
      "id": "step-1",
      "description": "descripción breve",
      "status": "pending | in_progress | completed | blocked",
      "files": ["archivos que tocará"],
      "tests": ["comandos para validarla"],
      "notes": "notas / resultado"
    }
  ],
  "files_read": ["archivos leídos"],
  "files_changed": ["archivos modificados/creados"],
  "tests_run": ["comando → resultado"],
  "known_failures": ["fallas aún sin resolver y su explicación"],
  "decisions": ["decisiones importantes y su motivo"],
  "next_action": "próximo paso concreto"
}
```

## Reglas de uso

1. **`files_changed`** debe reflejar lo que realmente mutó el disco
   (pásalo a `git status`), no lo que "se tenía idea" de modificar.
2. **`known_failures`**: si hay un test rojo o un error sin resolver, DEBE estar
   aquí con explicación y `next_action`. No concluyas con fallas mudas.
3. **`tests_run`**: registra el comando y el resultado (p. ej. `exit 0`,
   `17 passed`, `1 failed`). No escribas resultados que no se ejecutaron.
4. Si no es apropiado guardar el archivo en disco (p. ej. tarea efímera),
   mantén la misma estructura en el contexto de la conversación.
5. Al terminar, este archivo se considera "prueba" del proceso: plan → edición →
   validación → revisión. No lo borres a mitad de tarea.

## Persistência em MongoDB (memoria do modelo)

O estado e o histórico de validações se guardam também no seu **MongoDB local**
(com fallback automático a JSON se Mongo não está disponível).

**Base/coleções:** `cline_agent` → `tasks` (estado) e `validations` (histórico).

**Conexión:** por padrão `mongodb://localhost:27017/`. Se sobreescribe com
`MONGODB_URI`, `MONGODB_DB` e `TASK_ID` no `.env` ou variáveis de ambiente.

**Uso:**
```bash
.venv\Scripts\python.exe data\mongodb\scripts\init_mongo.py   # cria coleções/índices
.venv\Scripts\python.exe data\mongodb\scripts\memory.py state           # ver estado atual
.venv\Scripts\python.exe data\mongodb\scripts\memory.py validations 20  # historial
```

`tools/validate.py` registra cada corrida em `validations` automaticamente. Os tests
de `TaskStore` usam **fallback JSON** com paths temporales (não tocam o seu Mongo).

---

```json
{
  "objective": "Corregir el bug X en server.py",
  "plan": [
    { "id": "step-1", "description": "reproducir la falla con un test",
      "status": "completed", "files": ["tests/test_server.py"], "tests": ["unittest -v"], "notes": "test rojo reprodujo el bug" },
    { "id": "step-2", "description": "corregir la causa en server.py",
      "status": "in_progress", "files": ["app/server.py"], "tests": ["unittest -v", "validate.py"], "notes": "" }
  ],
  "files_read": ["app/server.py", "app/config.py"],
  "files_changed": ["tests/test_server.py"],
  "tests_run": ["python -m unittest discover -s tests -v → 1 fallo reproducido"],
  "known_failures": [],
  "decisions": ["No cambiar la firma pública de validate()"],
  "next_action": "editar app/server.py y re-ejecutar validate.py"
}
```