RELATÓRIO 08 — FASE 2: DEBUG VISÍVEL, TESTE DO AGENTE E LIMPEZA
Data: 10/09/2026
Estado: 154 testes OK · validate.py exit 0 · benchmark real 10/11 · commit realizado


==========================================================
1. RESUMO DA FASE
==========================================================

Continuação do relatório 07 (logging total). Nesta fase o objetivo foi
transformar os logs em DEBUG VISÍVEL e criar um teste ponta a ponta do
agente com registro no banco:

  - benchmark passa a deixar os debugs na pasta temp/ do projeto;
  - cada tarefa guarda TODAS as respostas do modelo e o veredito
    dos checks, mesmo quando falha;
  - novo teste do agente que grava em tasks E agent_runs, com
    finished True/False confirmado lendo de volta do Mongo;
  - limpeza de relatórios antigos e temp/ fora do git.


==========================================================
2. BENCHMARK: DEBUG VISÍVEL EM temp/
==========================================================

Problema encontrado:
  O run.py não passava work_root → os projetos de cada tarefa iam
  para o temp do WINDOWS e a pasta temp/ do projeto nunca era
  populada (o bench_005 antigo era resto de versão anterior).

Correção:
  tools/benchmarks/run.py agora usa <repo>/temp/bench_<task_id>/.

Novo: BenchmarkRunner._dump_debug — cada tarefa deixa na própria pasta:
  _debug_resposta.json
      task, tentativas (nº de chamadas ao modelo),
      respostas_brutas (TODAS as respostas, 1 por tentativa — dá
      para ver a evolução ruim→feedback→final),
      resposta_interpretada (files/edits escritos, edits_failed,
      edit_errors com o motivo exato de cada edição rejeitada).
  _debug_checks.txt
      veredito de cada check: nome, OK/FAIL e o motivo.

Para isso o LlamaExecutor passou a manter:

Corrida real (modelo Qwythos-9B, :8080, proxy de memória ativo):
  10/11 tarefas concluídas (91%)
  001 3/3 · 002 1/1 · 003 2/2 · 004 2/2 · 005 3/3 · 006 2/2
  007 1/1 · 008 1/1 · 009 2/2 · 010 1/1
  [X] 005X_feature_com_testes_longa → evoluiu de 0/12 para 10/12
  persistido em benchmark_runs_Q8_0 (Mongo)

Artefatos confirmados em temp/ (exemplos):
  bench_001/calc.py (34b), bench_005/string_utils.py +
  test_string_utils.py, bench_009/README.md + note + calc.py + run,
  bench_004/src/app.py + src/utils/helpers.py.

Achado de qualidade do modelo (visível graças ao dump):
  a 005X falha porque o 9B fecha o JSON do chat DENTRO do código:
  o string_utils.py termina com um '}' sobrando → SyntaxError
  'unmatched }'. Os 3 attempts cometem o mesmo erro (comparável
  no respostas_brutas). É qualidade do modelo, não bug de pipeline.
  Saídas possíveis: mais attempts, quebrar a instrução em partes
  menores, ou pós-processamento que detecta '}' solto no fim.


==========================================================
3. NOVO TESTE PONTA A PONTO: tools/agent_test.py
==========================================================

Motivação: o AgentRunner só gravava em tasks (save_state); agent_runs
era exclusivo do proxy. Faltava um teste que registrasse nos DOIS.

O script (tools/agent_test.py):
  1. cria projeto limpo em temp/agent_task_test/;
  2. dá a tarefa: criar saudacao.py com saudar(nome) → 'Olá, <nome>!'
     com type hints (AgentRunner + LlamaExecutor + AgentIdentity);
  3. verificação REAL: python -c "import saudacao; assert
     saudar('Vini') == 'Olá, Vini!'" — se falhar, vira feedback na
     próxima tentativa;
  4. grava em tasks (status completed/failed) e em agent_runs
     (task_id=agent-task-test, finished True/False);
  5. imprime o relatório LENDO os registros de volta do Mongo.

Resultado da corrida real:
  finalizado: True (1 tentativa, 0 retries)
  modelo escreveu saudacao.py tipado e o check passou.
  tasks → status completed, finished True
  agent_runs → finished True, attempts 1

==========================================================
4. BUGS PEGOS E CORRIGIDOS NESTA FASE
==========================================================

  a) Banner do main.py derrubava o boot em modo hidden:
     o emoji estoura UnicodeEncodeError quando o stdout é
     redirecionado (cp1252). O wrapper morria calado (logs de boot
     vazios). Correção: reconfigure(encoding="utf-8") antes do banner
     (mesmo padrão dos outros CLIs do projeto).

  b) Zumbis do proxy: 4 processos tools/proxy.py acumulados seguravam
     locks em stack_proxy.log/.err (por isso "arquivos travados").
     Mortos os 3 zumbis; proxy saudável reiniciado com redirects
     corretos; stack validada ponta a ponta (proxy 200 no /v1/models).

  c) Incidente do dotenv._log (relatório 07, seção 4) revalidado:
     recursão AppLogger→Config→resolve_mmproj→_log corrigida com
     path explícito + dedupe.

  d) test_identity.log órfão em temp/ (nenhum código aponta para ele)
     movido para logs/model/ como registro histórico.


==========================================================
5. LIMPEZA DE RELATÓRIOS
==========================================================

Descartados (estado morto, superseded — o que valia está no código
ou consolidado no relatório 04):
  01-caminhos-e-config-centralizados-v1.md  (refactor concluído)
  02-validacao-de-sistemas-v1.md            (validação pontual do dia)
  03-atualizacoes-servidor-e-proxy-v1.md    (snapshot de uma sessão)

Mantidos:
  04-agente-local-implementacao-v2.md   (referência de arquitetura)
  05-loop-guard-do-proxy-v1.md          (feature ativa em produção)
  07-logs-cobertura-completa-v1.md      (base desta fase)
  08 (este)                             (atual)


==========================================================
6. GIT
==========================================================

  - temp/* adicionado ao .gitignore (com !temp/.gitkeep): os debugs
    do benchmark/agente são gerados a cada corrida e NUNCA sobem pro
    git. Arquivos locais preservados.
  - temp/bench_005.../string_utils.py retirado do staged (era resto
    antigo que tinha entrado por engano).
  - Commit desta fase inclui: logging total (07), debug visível
    (runner/executor/parser), agent_test.py, memory.py "*",
    correções (banner, ps1, dotenv, etc.), relatórios (04, 05, 07, 08).


Correções de apoio:
  - memory.py agent-runs listava só task_id=current e o teste grava
    com task_id=agent-task-test → nada aparecia. Adicionado
    task_id="*" no HistoryCollection.list (Mongo: find({}); JSON:
    sem filtro) e o memory.py usa "*" para listar todas as execuções.

  raw_history   (lista com todas as respostas brutas)
  last_parsed   (a resposta interpretada, incluindo falhas de edição)

O dump nunca levanta (falha de debug não quebra o run).
