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
| 1 loopguard.tests | ✅ concluída | 1/1 | `tests/test_loopguard.py` criado (10 testes); vermelho confirmado (`ModuleNotFoundError`) |
| 2 loopguard.core | ✅ concluída | 1/1 | `loopguard.py` (99 linhas); 10/10 testes OK |
| 3 handler.integrate | ✅ concluída | 2/3 | Patch no `do_POST` + `_apply_loopguard`; correção: `session_id()` estático (evita duplicar count) |
| 4 suite.gate | ✅ concluída | 2/2 | pyright 0 erros (após fix de narrowing nos testes); **139 testes OK**; validate EXIT 0; diff OK |
| 5 live.validate | ✅ concluída | 2/2 | Ver detalhes abaixo |
| 6 docs.commit | ✅ concluída | 1/1 | Commit `6d33c9a`; este relatório atualizado com execução real |

## Resultado da validação ao vivo (Etapa 5)

**Tentativa 1 — bug real encontrado pelo teste ao vivo:** requests idênticas 2
e 3 retornaram **500**. Causa: aviso injetado como `role: "system"` no meio
das mensagens — o template de chat do Qwen só aceita system na posição 0.
**Correção:** injetar como `role: "user"` (`handler.py:54`). Reinício + reteste.

**Tentativa 2 — tudo verde:**

```
req 1: 200  req 2: 200  req 3: 200   (3 requests idênticas)

logs/agent.log:
  WARN proxy: LOOPGUARD sid=u-digiteexatamenteOK repeats=2 temp=0.7
  WARN proxy: LOOPGUARD sid=u-digiteexatamenteOK repeats=3 temp=0.9

resposta do modelo na request pós-nudge (prova de que o aviso chega):
  "Entendido. A instrução era para digitar exatamente \"OK\"."

check_runs.py (Mongo):
  1 doc/conversa, task_id=u-digiteexatamenteOK,
  requests_count=6, timeline correta, agent_runs->mongo
```

**Comportamento confirmado:** 1ª passa silenciosa → 2ª nudge + temp 0.7 →
3ª+ aviso forte + temp 0.9 → Mongo segue gravando 1 doc por conversa.

### Ajustes de rota registrados durante a execução
- `SessionRegistry.session_id()` (estático) em vez de `touch()` — tocar de
  novo duplicaria o contador da sessão (o recorder já toca).
- Aviso como mensagem `user`, não `system` (limitação do template Qwen).
- Testes corrigidos p/ narrowing do pyright (`assert x is not None`).

## STATUS FINAL DA FASE 2

```
STATUS: CONCLUÍDO
IMPLEMENTADO: LoopGuard (detecção por hash + intervenção progressiva)
              integrado ao ProxyHandler, fail-open, thread-safe.
VERIFICADO:   139 testes OK | pyright 0 erros | validate EXIT 0 |
              live: 3× 200, LOOPGUARD disparou 2×, Mongo íntegro.
ARQUIVOS:     app/services/proxy/loopguard.py (novo),
              app/services/proxy/handler.py, app/services/proxy/server.py,
              tests/test_loopguard.py (novo), docs/RELATORIO-v2.md.
PENDÊNCIAS:   (1) print cosmético agent_runs em tools/agent.py:111;
              (2) gate de sintaxe ast.parse ainda não recolocado;
              (3) expiração de sessões antigas no LoopGuard (memória
              cresce devagar; limiar baixo em uso real).
```

**Regras do ciclo (do prompt operacional):** máx. 3 tentativas/etapa; 2
repetições da mesma ação abrem circuit breaker; exit 0 não é prova — efeito
real observado é; `BLOQUEADO: <motivo>` quando não houver progresso.

---

# Fase 2.5 — Saúde do modelo + benchmark consolidado (2026-09-08 21:11–21:20)

## Bateria executada

1. **Doctor** (`tools/doctor.py`) → **SAUDÁVEL** (0 falhas, 1 aviso menor:
   "memória vazia" no state atual).
2. **Benchmark real** (`tools/benchmarks/run.py --real`) → **3 baterias**,
   todas persistidas no Mongo (`benchmark_runs`; 29 corridas no histórico).
3. **Suíte completa** (15 arquivos em `tests/`) → **139 testes OK** (16.1s).

## Conformidade com o card oficial (HuggingFace)

| Item | Card oficial | Nossa config | Status |
|---|---|---|---|
| CTX | modelo 1M | 100352 | ✅ |
| Visão | text-only fine-tune | MM_PROJ_ENABLED=0 | ✅ |
| Sampling | **temp 0.6, top_p 0.95, top_k 20, rep 1.05** | temp **0.3**, top_k 40, top_p 0.9 | ⚠️ fora |
| max_tokens | **16.384 recomendado** | 2048 (executor) | ⚠️ fora |
| Loops | "T≤0.3 pode entrar em repetition loops" | LoopGuard compensa no proxy | 🟡 paliativo |

## Benchmark — 3 baterias

| Bateria | Placar | Tempo médio | Retries |
|---|---|---|---|
| 1 (21:12) | 9/10 (90%) | 7.45s | 0.1 |
| 2 (21:18) | 9/10 (90%) | 7.58s | 0.0 |
| 3 (21:20) | 8/10 (80%) | 4.98s | 0.2 |
| **TOTAL** | **26/30 — 86.7%** | **6.67s** | **0.1** |

| Tarefa | Runs | Checks | Veredito |
|---|---|---|---|
| 001 criar_funcao | 3/3 | 9/9 | 💯 |
| 002 editar_funcao | 3/3 | 3/3 | 💯 |
| 003 bug_simples | 3/3 | 6/6 | 💯 |
| 004 bug_multi_arquivo | 3/3 | 6/6 | 💯 |
| **005 feature_com_testes** | **0/3** | **3/9** | 🔴 falha sistemática |
| 006 refactor_sem_quebrar | 3/3 | 6/6 | 💯 |
| 007 interpretar_erro | 3/3 | 3/3 | 💯 |
| 008 projeto_desconhecido | 2/3 | 2/2 | 🟡 intermitente |
| 009 codigo_e_docs | 3/3 | 6/6 | 💯 |
| 010 consertar_incompleto | 3/3 | 3/3 | 💯 |

## Diagnóstico da 005 (evidência nos RAW_CONTENT de logs/bench-*.log)

O modelo **gera o código correto** (slugify + testes) mas o JSON sai
malformado em ~2 de 3 respostas:

- trailing comma → `json.loads` rejeita;
- aspa de fechamento esquecida no meio do conteúdo.

Resultado: `FILES_PARSED: []` → nada vai ao disco → os checks de teste
falham. **É defeito do parser, não do modelo.** A 008 falhou pelo mesmo
mecanismo, de forma intermitente.

## Correções apontadas (pendências 4 e 5)

1. **Reparo de JSON no `_parse_files`** (executor + agente): tolerar
   trailing commas e fechar string/objeto truncado antes de desistir.
   → converte a 005 em ponto cheio com conteúdo que o modelo já produz.
2. **max_tokens 2048 → 16384** no `LlamaExecutor` (recomendação explícita
   do card) → evita truncamento no meio do JSON em tarefas multi-arquivo.
3. (Já aprovado, aguardando restart) sampling p/ card: temp 0.6,
   top_p 0.95, top_k 20 — ataca a causa dos repetition loops na fonte.

## STATUS FASE 2.5

```
STATUS: CONCLUÍDO (medição) — correções listadas pendentes de aprovação
VERIFICADO: doctor SAUDÁVEL | 3 baterias no Mongo | 139 testes OK
PRÓXIMA AÇÃO: implementar reparo de JSON + max_tokens 16384 (com testes)
```
