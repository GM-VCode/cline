# 📁 `docs\relatorios\` — Histórico de relatórios do projeto

Pasta onde ficam os **relatórios técnicos** (diários/por fase) das
sessões de desenvolvimento da LunarIA/Qwythos-9B. Cada arquivo documenta
o que foi feito, o porquê, as decisões e a validação daquela etapa —
servindo de **memória de projeto** (complemento aos estados em
`data\json\task-state.json` e às coleções do Mongo).

## Arquivos

| Arquivo | O que documenta |
|---|---|
| `01-caminhos-e-config-centralizados-v1.md` | Centraliza caminhos/config em `project_path` (fonte única) + zerar diagnósticos Pylance/Pyright |
| `02-validacao-de-sistemas-v1.md` | Validação geral dos sistemas (sem consertar): infra, Mongo, logs, API pública |
| `03-atualizacoes-servidor-e-proxy-v1.md` | Atualizações pós-commit: servidor chamam VRAM/tool calls, proxy de memória, config otimizada (FA/parallel/KV) |
| `04-agente-local-implementacao-v2.md` | Implementação do agente local (fluxo auditar→planejar→editar→validar→corrigir) |
| `05-loop-guard-do-proxy-v1.md` | Fase 2: `LoopGuard` do proxy (detecção de loop por respostas idênticas) |

## Convenção de nomes

`NN-assunto-vX.md`
- `NN` — ordem cronológica do relatório (01, 02, ...)
- `assunto` — o que o relatório cobre (específico, não "vago")
- `vX` — versão/iteração do tema (v1, v2, ...) quando revisita o mesmo assunto

## Nota

Relatórios antigos continuam **referenciáveis no git** (os `git mv`
preservaram o histórico) — apontar para o caminho novo nos docs/comentários
que os citam (ex.: `docs/relatorios/04-...-v2.md`).

- Não confunde com `docs\` raiz: esta pasta é só para os **relatórios**;
  outros documentos de apoio podem morar na raiz de `docs\`.