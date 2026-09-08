# RELATORIO v2 — Fase 2: Loop Guard do Proxy

**Data de início:** 2026-09-08
**Commit base:** `53b761f` (docs: relatorio 4)
**Estado do ambiente na auditoria:** Windows 10 (Git Bash/MINGW64), Python 3.14.7
(`.venv`), git limpo, modelo `:8080` UP (PID 12644), proxy `:8081` UP (PID 13716).

---

## Problema (evidência real da sessão)

O modelo gerou 1 comando gigante encadeado (15 `echo > ...`), o Cline abortou,
e no retry — mesmo contexto + `TEMP 0.3` (determinístico) — o modelo respondeu
**idêntico**. Após 5 chamadas idênticas consecutivas, o loop guard do Cline
parou a task. Causa: **nenhum estímulo no retry para mudar de estratégia**.

## Solução: Loop Guard no proxy (camada que controlamos)

Sem mexer no Cline (client) nem no modelo. Fail-open: se o guard falhar, o
proxy funciona como hoje.

```
request → hash das mensagens (por sessão)
  1ª vez igual       → repassa normal (+ regra de estilo na 1ª da sessão)
  2ª vez igual       → injeta aviso "mude de estratégia, comandos menores"
                       + temperature 0.3 → 0.7 (quebra determinismo)
  3ª+ vez igual      → aviso mais forte + temperature 0.9
```

---

## Plano por etapas (uma ação por vez, critério objetivo)

### Etapa 1 — loopguard.tests (TDD: comportamento primeiro)
- **Objetivo:** definir o contrato do guard em testes.
- **Pré-condições:** ambiente auditado; suíte atual verde.
- **Arquivos:** `tests/test_loopguard.py` (novo).
- **Ações:** escrever testes — hash estável do body; contagem por sessão;
  vereditos `pass`/`nudge`/`strong`; texto do aviso; bump de temperature;
  fail-open (exceção interna → repassa sem mexer).
- **Sucesso:** testes existem e falham por falta da implementação (import).
- **Verificação:** `python -m unittest tests.test_loopguard -v`.
- **Próxima:** etapa 2.

### Etapa 2 — loopguard.core
- **Objetivo:** implementar a classe `LoopGuard`.
- **Pré-condições:** etapa 1 com testes definidos.
- **Arquivos:** `app/services/proxy/loopguard.py` (novo, ≤120 linhas).
- **Ações:** classe thread-safe com `request_hash(body)`, `register(sid, h)`
  e `verdict(sid, h)` → `(aviso|None, temperature|None)`.
- **Sucesso:** `python -m unittest tests.test_loopguard -v` 100% OK.
- **Verificação:** mesma suíte + `pyright app/services/proxy/loopguard.py`.
- **Próxima:** etapa 3.

### Etapa 3 — handler.integrate
- **Objetivo:** ligar o guard no `do_POST` sem alterar comportamento de
  sessões/recorder existentes.
- **Pré-condições:** etapa 2 verde.
- **Arquivos:** `app/services/proxy/handler.py` (patch cirúrgico ~12 linhas).
- **Ações:** calcular hash → registrar → se veredito, injetar mensagem de
  sistema no `body["messages"]` e sobrescrever `temperature` → repassar.
- **Sucesso:** suíte completa do proxy continua verde; requests sem repetição
  seguem byte a byte iguais (guard silencioso).
- **Verificação:** `python -m unittest discover -s tests` + diff revisado.
- **Próxima:** etapa 4.

### Etapa 4 — suite.gate
- **Objetivo:** gate oficial do projeto.
- **Pré-condições:** etapa 3 integrada.
- **Ações:** `compileall` → suíte completa → `pyright` → `tools/validate.py` →
  `git diff --check`.
- **Sucesso:** tudo verde.
- **Verificação:** logs dos comandos.
- **Próxima:** etapa 5.

### Etapa 5 — live.validate
- **Objetivo:** provar com o modelo real.
- **Pré-condições:** gate verde; proxy reiniciado com o código novo.
- **Ações:** repetir a mesma request 2× via `curl :8081` e conferir no
  `logs/proxy.log` a injeção do aviso + temperature bump; conferir no Mongo
  que a gravação continua correta (1 doc/conversa).
- **Sucesso:** 2ª request idêntica registra `loopguard: nudge` no log e
  `agent_runs->mongo` segue normal.
- **Verificação:** trechos do log + `check_runs.py`.
- **Próxima:** etapa 6.

### Etapa 6 — docs.commit
- **Objetivo:** documentar e fechar a fase.
- **Ações:** atualizar este arquivo com o resultado real de cada etapa;
  marcar pendência do `relatorio_4.md` como resolvida; commit.
- **Sucesso:** commit limpo, relatório coerente com o que foi feito.

---

## Registro de execução (atualizar a cada etapa)

| Etapa | Status | Tentativa | Evidência |
|---|---|---|---|
| 0 auditoria | ✅ concluída | 1/1 | OS/shell/python/git/portas confirmados |
| 1 loopguard.tests | ⏳ pendente | — | — |
| 2 loopguard.core | ⏳ pendente | — | — |
| 3 handler.integrate | ⏳ pendente | — | — |
| 4 suite.gate | ⏳ pendente | — | — |
| 5 live.validate | ⏳ pendente | — | — |
| 6 docs.commit | ⏳ pendente | — | — |

**Regras do ciclo (do prompt operacional):** máx. 3 tentativas/etapa; 2
repetições da mesma ação abrem circuit breaker; exit 0 não é prova — efeito
real observado é; `BLOQUEADO: <motivo>` quando não houver progresso.
