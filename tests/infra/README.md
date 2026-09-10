# 🧱 `tests\infra\` — Testes de infraestrutura

Cobre a base que sustenta tudo: configuração, servidor, diagnóstico e logging.

## Arquivos

| Arquivo | O que testa |
|---|---|
| `test_config.py` | `Config`: leitura do `.env`, defaults, validações (CTX, REASONING...) |
| `test_server.py` | `LlamaServer`: montagem de argumentos, kill_old, health |
| `test_doctor.py` | `tools\doctor.py`: checagens de saúde (paths, config, logs) |
| `test_logger.py` | `AppLogger`: níveis, split por arquivo, rotação, traceback |
