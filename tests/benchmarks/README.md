# 📊 `tests\benchmarks\` — Testes do benchmark de tarefas

Cobre o benchmark **do projeto** (catálogo de tarefas 001–010 + 005X):
runner, checks e relatório persistido no Mongo.

## Arquivos

| Arquivo | O que testa |
|---|---|
| `test_benchmarks.py` | Runner de ponta a ponta (LocalExecutor determinístico) |
| `test_benchmark_report.py` | `BenchmarkReport`: métricas do resumo + persistência agrupada por modelo |
| `test_benchmark_checks.py` | Fábricas de checks (unittest real, comportamento real) |

## Relacionado

- Bench de **modelo de chat** (Copilot etc.) está em `tests\chat_test\`.
