# 🧭 Fluxo disciplinado de trabalho (reglas de Cline)

Estas reglas guiam o comportamento do agente (Cline) quando trabalha sobre
este repo. Se aplicam a **qualquer** tarefa de código. O objetivo não é generar
mais código, senão um processo confiable de engenharia.

## 1. Antes de tocar nada: auditar

1. Lista a estrutura do projeto (ignora `.git`, `node_modules`, `.venv`,
   `__pycache__`, `dist`, `build` e binarios grandes).
2. Leia o README, a config, o entry point e os módulos relacionados.
3. Revisa o estado de Git (`git status`) e **não pises** cambios do usuário
   (p. ej. `.env`).
4. Busca TODOs/FIXME/imports rotos **sólo** para entender; não edites código que
   não forma parte da tarefa.

Presenta un plan curto: objetivo, archivos a modificar, archivos que NÃO se
tocan, riscos, estrategia de tests e critério de conclusión.

## 2. Dividir em etapas pequenas

- Cada etapa: objetivo específico, archivos, pre-condición, cambio esperado e
  **su** validación.
- No implementes um sistema grande de uma vez. Valida cada etapa antes da
  siguiente.

## 3. Leer antes de editar

- Nunca edites um archivo sin leelo antes (o el fragmento relevante).
- Antes de crear una función/clase/arg/ruta/variable: busca si ya existe, onde
  se define e quién la usa. **No inventes nombres** que não estén no proyecto.
- Preserva la interfaz existente salvo que la tarefa exija camниarla; si cambia,
  atualiza todos sus consumidores.

## 4. Alteraciones pequenas e verificables

- Prefer sagura patches pequenos a reescrebir archivos completos.
- Trás cada edición: confirma éxito, **relee** el archivo, busca duplicados,
  líneas truncadas e indentación incorrecta.
- Si la edición falha: no lo finjas. Relee, verifica, reduce el patch o cambia
  de método, y vuelve a confirmar.

## 5. Estado estructurado da tarefa

- Mantén `.task-state.json` (em `data/json/`, ver `02-task-state.md`) e atualícelo em
  cada etapa: objetivo, plan con status, archivos lidos/cambiados, tests
  executados, falhas conhecidas, decisiones e próxima acción.
- **Nunca** declares a tarefa concluida con falhas pendentes sin explicación.

## 6. Consistencia entre definições e usos

- Verifica: funciones↔chamadas, classes↔imports, args de CLI↔código que los lê,
  config↔uso, rutas↔consumidores, nomes documentados↔implementados.
- Busca referências a atributos (`args.input`, `args.url`, `args.config`,
  `args.patterns`) sin definición en el parser.

## 7. Testear depois de editar

Orden de validación:

```bash
python -m compileall -q app data/mongodb main.py tools tests
python -m unittest discover -s tests -v
python tools/validate.py
git diff --check
```

- Si no hay tests para el comportamento, créalos mínimos (no artificiales).
- Nunca des por hecho que funciona porque "el código existe".

## 8. Corrigir erros em loop

```
executar → código de salida → mensaje completa → archivo:línea
→ hipótesis → corrigir causa → re-ejecutar → verificar no-regresión
```

Repite hasta: el test pase, la falha sea comprobadamente externa, ou haya un
bloqueo real (entonces reporta comando, error, intentos e acción humana
necesaria).

## 9. No declarar éxito prematuro

No uses "está listo/funcionando/implementado" solo porque los archivos se
crearon. Antes de concluir: sintaxis, imports, tests, comando principal, diff
revisado, sin falhas conhecidas, e documentación coerente.

## 10. Revisar o próprio trabalho (estilo PR)

Bug lógico, casos de error, entradas inválidas, regresiones, imports olvidados,
archivos que faltaron, cambios innecesarios, código duplicado, seguridad e
documentación desatualizada. Corrige e re-testea.

## 11. Contexto inteligente

Prioriza: sistema → objetivo → estructura → archivos relacionados → interfaces →
cambios recientes → erros de test → pendientes. Preserva objetivo, restricciones,
decisiones, archivos, tests que falharam e mensajes de error aunque resumas.

## 12. Recuperación de fallas de herramienta

**Leer:** confirma ruta, verifica existencia, reduce el rango, no inventes
contenido. **Editar:** relee, reduce patch, usa contexto exacto, verifica.
**Shell:** captura exit code, identifica la shell, adapta la sintaxis.
**Test:** corrige la causa, no el síntoma; re-ejecuta el test y luego la regresión.

## 13. Seguridad e escopo

- No expongas `.env`, tokens, claves ni cookies. No los imprimas.
- No edites archivos fora do escopo sin justificación.
- No ejecutes comandos destructivos si hay un equivalente seguro.
- Antes de algo destructivo o irreversible: **detente e pregunta**.
- Preserva cambios do usuário (`.env` deste repo está modificado a propósito).

## 14. No inventar requisitos

Alternativa más conservadora y reversible; registra a suposición. No añadas
dependencias/frameworks/servicios sin necesidad real. No conviertas una tarefa
pequeña en una reescritura.

---

## Critério de aceptação (ponta a ponta)

Una tarefa con un bug deve poder ejecutarse así:

1. recibir un proyecto pequeño con un bug
2. localizar los archivos relacionados
3. explicar el plan
4. editar **sólo** lo necesario
5. ejecutar el test existente
6. interpretar una falha
7. corrigir el problema
8. ejecutar el test de novo
9. revisar el diff
10. informar el resultado con honestidad

Si en cualquier momento el `.env`, `models/`, `tools/visao/` ou `bat/` deberían
cambiarse, **explícalo e pide permiso** antes de hacerlo.