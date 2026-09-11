RELATÓRIO 07 — LOGGING: COBERTURA COMPLETA DO PROJETO
Data: 10/09/2026
Resultado: 154 testes OK · validate.py exit 0 · stack online ponta a ponta


==========================================================
1. CRIADOS DO ZERO (não existia log nenhum)
==========================================================

Agente (destino: logs/app/agent.log)
  app/agent/apply.py
      edit REJEITADO (WARN, com o motivo) e edit aplicado (DEBUG).
  app/agent/checks.py
      check falhou com exit != 0 (WARN, com comando e saída);
      check não executou / timeout (ERROR); run shell idem (WARN).
  app/agent/context.py
      getsize ou leitura de arquivo falha no snapshot (WARN).
  app/agent/runner/compose.py
      tamanho do prompt composto (DEBUG) — pega prompt estourando
      contexto.
  app/agent/runner/core.py
      executor estoura exceção (ERROR, com o número da tentativa) —
      antes só retornava o erro no dict, calado.

Benchmarks (destino: logs/model/)
  tools/benchmarks/runner.py            → benchmark.log
      TASK / BEGIN / RESULT de cada tarefa, agora com executor_error
      (o RESULT antigo não mostrava O QUE falhou).
  tools/benchmarks/executor_llama       → executor.log
      EXECUTOR CALL e RESPONSE RAW de cada chamada ao modelo.
  tools/benchmarks/executor_llama/parser.py → executor.log
      resposta sem JSON, JSON irrecuperável (loads + repair falharam),
      JSON que não é objeto, resposta sem content, falha ao gravar
      arquivo gerado. Tudo silencioso antes.
  tools/benchmarks/tasks/core.py        → benchmark.log
      check do benchmark estoura exceção.
  tools/benchmarks/report.py            → benchmark.log
      falha ao salvar o resumo (era except: pass — a corrida podia
      não ser salva e ninguém ficava sabendo).

Memória / Mongo (destino: logs/app/fallback.log)
  data/mongodb/store/task_store.py
      FALLBACK ATIVADO: Mongo indisponível → JSON/temp, com motivo e
      destino; erros de runtime também.
  data/mongodb/store/json_file.py
      JSON corrompido ou falha de escrita. Observação: leitura de
      arquivo inexistente NÃO loga (é estado normal na primeira vez).
  data/mongodb/connection.py
      falha de conexão na origem, com a URI e o motivo.
  data/mongodb/scripts/memory.py
      CLI avisa no console quando Mongo está off e lê do fallback
      (o registro fica no fallback.log via TaskStore).

Configuração (destino: logs/app/{warn,error}.log)
  project_path/dotenv.py
      .env ausente (WARN) ou ilegível (ERROR); MODEL_PATH vazio sem
      modelo resolvível (ERROR — o server não sobe); MM_PROJ_PATH
      ambíguo ou sem correspondência (WARN); valor inválido convertido
      para default em as_int/as_opt (WARN, com chave e valor).
  data/mongodb/store/runtime.py
      o loader duplicado foi substituído pelo load_dotenv central:
      mesmo parsing e herda o log de falha.
  project_path/config.py
      paths novos: BENCHMARK_LOG, EXECUTOR_LOG, FALLBACK_LOG,
      CLINE_USE_LOG.

Chat-bench do Cline (destino: logs/model/cline-use.log)
  tools/cline_use/run.py
      tentativa que falha (ERROR), tarefa que estoura exceção (ERROR),
      pontuação final da corrida (INFO/WARN).
  tools/cline_use/grader.py
      cada check FAIL com task, nome do check e detalhe (WARN).
      Antes: zero log, tudo ia só pro stdout.



Infra e ferramentas
  app/services/server/__init__.py → logs/app/info.log
      llama-server morre com exit != 0 (antes: crash calado).
  app/services/proxy/handler.py → logs/app/agent.log
      probe.feed falho (DEBUG; o fail-open foi mantido).
  tools/validate.py → logs/app/info.log
      corrida não registrada no histórico (antes except: pass).
  tools/doctor.py → logs/app/info.log
      check do doctor estoura exceção (com o nome do check).
  bat/INICIAR-STACK-COMPLETA.ps1
      caminhos antigos nas linhas 50 e 75 corrigidos: apontavam para
      logs\stack_server.err.log / logs\stack_proxy.err.log (fora da
      subpasta); agora apontam para logs\proxy_and_server\.
  main.py
      banner de boot no console: "🤖 LunarIA — IA LOCAL ON" com
      modelo, API e pasta de logs.

Novos loggers centralizados em app/agent/debug.py (mesmo padrão do
get_agent_logger, override por env para os tests):
  get_benchmark_logger(), get_executor_logger(),
  get_fallback_logger(), get_cline_use_logger().


==========================================================
2. JÁ TINHAM LOG (conferidos, não mexi)
==========================================================

  tools/logger/ (AppLogger)
      split por nível em logs/app/{debug,info,warn,error,critical}.log.
  app/agent/debug.py::get_agent_logger
      logs/app/agent.log — agente, loop de ações, proxy, memória.
  tools/proxy.py
      JÁ LOGAVA em dois lugares: os print vão para
      logs/proxy_and_server/stack_proxy.log (redirect do script da
      stack) e os log.info/warn vão para logs/app/agent.log.
      A impressão de "sem log" era essa separação.
  app/services/server (início, PID, PRONTO, CTRL+C, health falhou)
      logs/app/info.log.
  tools/doctor.py (resumo) e tools/validate.py (resultado final)
      logs/app/info.log.
  tools/cline_use/run.py (class Tee)
      log por corrida em logs/model/<MODELO>_<timestamp>.log.
  data/mongodb/store/state.py e history.py
      falhas via error_sink → _catch_error → fallback.log.
  tests/
      logs redirecionados a temp via AGENT_LOG_PATH — higiene
      deliberada para não poluírem o log real.


==========================================================
3. DE PROPÓSITO SEM LOG (e o porquê)
==========================================================

  project_path/paths.py
      Cálculo puro de caminhos: sem I/O, sem except, não falha.
      Um log aqui dispararia em todo import do projeto — só ruído.
  tools/cline_use/tasks.py
      Apenas definição de dados das tarefas; nada executa lá.
  tools/logger/ (writer, rotator, app_logger)
      O logging não pode depender do logging — recursão garantida.
  dotenv.py / runtime.py (casos de sucesso)
      Ler e parsear com sucesso não é evento; só a falha interessa.
  data/mongodb/connection.py close()
      Fechamento silencioso é inofensivo.
  tests/
      Cobertos pela regra de higiene (paths em temp).


==========================================================
4. INCIDENTE CORRIGIDO DURANTE A TAREFA
==========================================================

A primeira versão do _log do dotenv.py criava o AppLogger com o path
padrão → AppLogger chama Config() → Config chama resolve_mmproj →
resolve_mmproj chama _log → recursão infinita: ~160 mil linhas de
flood no warn.log e processos em loop.

Correção aplicada (causa, não sintoma):
  - o _log do dotenv monta o path direto do ProjectPath, SEM
    instanciar Config() (impossível recorrer);
  - mapa nível → arquivo (debug/info/warn/error/critical.log);
  - guard de dedupe: mensagem idêntica não repete (anti-flood).

Os 3 processos em loop foram mortos, o warn.log foi limpo e tudo foi
revalidado: 154 testes OK, validate exit 0, smoke sem recursão.


==========================================================
5. PENDÊNCIA DE CONFIG (achado real, decisão do Vini)
==========================================================

O .env tem MM_PROJ_PATH apontando para um caminho absoluto com
backslash SIMPLES (C:\Users\...\tools\visao\Qwythos-...-mmproj-BF16.gguf).
O early-return de caminho absoluto no resolve_mmproj testa backslash
DUPLO, então cai no WARN "nenhum .gguf correspondente" e o mmproj não
é carregado. O doctor também acusa isso.

Duas saídas:
  a) corrigir o resolve_mmproj para aceitar backslash simples; ou
  b) ajustar o MM_PROJ_PATH no .env.

Não mexi sem sua autorização (regra do projeto: .env e visao/ exigem
permissão prévia).
