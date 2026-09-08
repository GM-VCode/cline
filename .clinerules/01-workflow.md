# 🧭 Fluxo disciplinado de trabalho (regras do Cline)

Estas regras orientam o comportamento do agente (Cline) quando ele trabalha neste repositório. Elas se aplicam a **qualquer** tarefa de código. O objetivo não é gerar mais código, mas sim estabelecer um processo confiável de engenharia.

## 1. Antes de tocar em qualquer coisa: auditar

1. Liste a estrutura do projeto (ignore `.git`, `node_modules`, `.venv`, `__pycache__`, `dist`, `build` e binários grandes).

1. Leia o README, a configuração, o ponto de entrada e os módulos relacionados.

1. Revise o estado do Git (`git status`) e **não sobrescreva** as alterações do usuário (por exemplo, `.env`).

1. Procure TODOs/FIXMEs/importações quebradas **somente** para entender o contexto; não edite código que não faça parte da tarefa.

Apresente um plano curto: objetivo, arquivos a modificar, arquivos que **NÃO** serão alterados, riscos, estratégia de testes e critério de conclusão.

## 2. Dividir em etapas pequenas

- Cada etapa deve ter: objetivo específico, arquivos envolvidos, pré-condição, alteração esperada e **sua** validação.

- Não implemente um sistema grande de uma só vez. Valide cada etapa antes da próxima.

## 3. Ler antes de editar

- Nunca edite um arquivo sem tê-lo lido antes (ou pelo menos o trecho relevante).

- Antes de criar uma função/classe/argumento/rota/variável: procure se já existe, onde é definido e quem o utiliza. **Não invente nomes** que não estejam no projeto.

- Preserve a interface existente, a menos que a tarefa exija alterá-la; se ela mudar, atualize todos os seus consumidores.

## 4. Alterações pequenas e verificáveis

- Prefira patches pequenos e seguros a reescrever arquivos completos.

- Após cada edição: confirme o sucesso, **releia** o arquivo, procure duplicações, linhas truncadas e indentação incorreta.

- Se a edição falhar: não finja que funcionou. Releia, verifique, reduza o patch ou mude o método e confirme novamente.

## 5. Estado estruturado da tarefa

- Mantenha `.task-state.json` (em `data/json/`, consulte `02-task-state.md`) e atualize-o a cada etapa: objetivo, plano com status, arquivos lidos/alterados, testes executados, falhas conhecidas, decisões e próxima ação.

- **Nunca** declare a tarefa concluída com falhas pendentes sem explicá-las.

## 6. Consistência entre definições e usos

- Verifique: funções↔chamadas, classes↔importações, argumentos da CLI↔código que os lê, configuração↔uso, rotas↔consumidores, nomes documentados↔implementados.

- Procure referências a atributos (`args.input`, `args.url`, `args.config`, `args.patterns`) sem definição no parser.

## 7. Testar depois de editar

Ordem de validação:

```bash
python -m compileall -q app data/mongodb main.py tools tests
python -m unittest discover -s tests -v
python tools/validate.py
git diff --check
```

- Se não houver testes para o comportamento, crie testes mínimos (não artificiais).

- Nunca presuma que funciona apenas porque “o código existe”.

## 8. Corrigir erros em loop

```
executar → código de saída → mensagem completa → arquivo:linha
→ hipótese → corrigir a causa → executar novamente → verificar a não regressão
```

Repita até que: o teste passe, a falha seja comprovadamente externa ou exista um bloqueio real. Nesse último caso, informe o comando, o erro, as tentativas realizadas e a ação humana necessária.

## 9. Não declarar sucesso prematuramente

Não use “está pronto/funcionando/implementado” apenas porque os arquivos foram criados. Antes de concluir: verifique a sintaxe, as importações, os testes, o comando principal e o diff; confirme que não há falhas conhecidas e que a documentação está coerente.

## 10. Revisar o próprio trabalho (estilo PR)

Verifique: bugs lógicos, casos de erro, entradas inválidas, regressões, importações esquecidas, arquivos ausentes, alterações desnecessárias, código duplicado, segurança e documentação desatualizada. Corrija e teste novamente.

## 11. Contexto inteligente

Priorize: sistema → objetivo → estrutura → arquivos relacionados → interfaces → alterações recentes → erros de teste → pendências. Preserve o objetivo, as restrições, as decisões, os arquivos, os testes que falharam e as mensagens de erro, mesmo ao resumir.

## 12. Recuperação de falhas de ferramentas

**Leitura:** confirme o caminho, verifique a existência, reduza o intervalo e não invente conteúdo. **Edição:** releia, reduza o patch, use o contexto exato e verifique. **Shell:** capture o código de saída, identifique o shell e adapte a sintaxe. **Teste:** corrija a causa, não o sintoma; execute novamente o teste e, em seguida, a regressão.

## 13. Segurança e escopo

- Não exponha `.env`, tokens, chaves nem cookies. Não os imprima.

- Não edite arquivos fora do escopo sem justificativa.

- Não execute comandos destrutivos se houver uma alternativa segura.

- Antes de realizar algo destrutivo ou irreversível: **pare e pergunte**.

- Preserve as alterações do usuário (`.env` deste repositório foi modificado de propósito).

## 14. Não inventar requisitos

Escolha a alternativa mais conservadora e reversível; registre a suposição. Não adicione dependências, frameworks ou serviços sem necessidade real. Não transforme uma tarefa pequena em uma reescrita.

## 15. Auto-validação antes de entregar (OBRIGATORIO)

Aplica a **qualquer** tarefa de código (Cline, agente, benchmark, proxy):

1. **Antes de declarar "pronto/completo", execute** o que você acaba de criar ou editar: rode o teste ou comando de verificação do próprio projeto. Não baste dizer que "deveria funcionar".

1. **Sequência mínima de entrega:** criar/editar → executar → **corrigir o erro real** → re-executar → só então entregar.

1. **Nunca repita** o mesmo comando que já falhou igual: mude a abordagem ou explique o bloqueo (use `BLOQUEADO: <motivo>`).

1. **Nunca peça validação ao usuário como parte da entrega.** Se o check falha, corrija e re-teste. O usuário não é runner de testes.

1. Se não existe comando de verificação (projeto sem tests), execute ao menos un smoke que demonstre que funciona (import, `--help`, run mínimo). Documente o que rodó e a saída.

1. O estado da tarefa deve refletir isso: em `data/json/task-state.json` registre `tests_run` com o comando real e seu resultado; `known_failures` vazio o explicado.

---

## Critério de aceitação (ponta a ponta)

Uma tarefa com um bug deve poder ser executada da seguinte forma:

1. receber um projeto pequeno com um bug;

1. localizar os arquivos relacionados;

1. explicar o plano;

1. editar **somente** o necessário;

1. executar o teste existente;

1. interpretar uma falha;

1. corrigir o problema;

1. executar o teste novamente;

1. revisar o diff;

1. informar o resultado com honestidade.

Se, em algum momento, `.env`, `models/`, `tools/visao/` ou `bat/` precisarem ser alterados, **explique o motivo e peça permissão** antes de fazer isso.