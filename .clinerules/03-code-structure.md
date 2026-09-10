# 🐍 Regras de código — padrão de projeto organizado (Python Zen)

## ⚖️ LEI MÁXIMA — Zen do Python (PEP 20) · nível máximo de importância

> **Todas as regras deste projeto derivam dos 19 aforismos abaixo.**
> Nenhuma regra, código ou decisão pode contradizê-los. Em conflito? Vence o Zen.

Original canônico (`import this`):

```text
Beautiful is better than ugly.
Explicit is better than implicit.
Simple is better than complex.
Complex is better than complicated.
Flat is better than nested.
Sparse is better than dense.
Readability counts.
Special cases aren't special enough to break the rules.
Although practicality beats purity.
Errors should never pass silently.
Unless explicitly silenced.
In the face of ambiguity, refuse the temptation to guess.
There should be one-- and preferably only one --obvious way to do it.
Although that way may not be obvious at first unless you're Dutch.
Now is better than never.
Although never is often better than *right* now.
If the implementation is hard to explain, it's a bad idea.
If the implementation is easy to explain, it may be a good idea.
Namespaces are one honking great idea -- let's do more of those!
```

Tradução (referência):

1. Bonito é melhor que feio.
2. Explícito é melhor que implícito.
3. Simples é melhor que complexo.
4. Complexo é melhor que complicado.
5. Plano é melhor que aninhado.
6. Esparso é melhor que denso.
7. Legibilidade conta.
8. Casos especiais não são especiais o suficiente para quebrar as regras.
9. Embora a praticidade vença a pureza.
10. Erros nunca devem passar em silêncio.
11. A menos que sejam explicitamente silenciados.
12. Diante da ambiguidade, recuse a tentação de adivinhar.
13. Deve haver um — e preferencialmente apenas um — modo óbvio de fazer isso.
14. Embora esse modo possa não ser óbvio à primeira vista, a menos que você seja holandês.
15. Agora é melhor que nunca.
16. Embora "nunca" seja frequentemente melhor que "agora mesmo".
17. Se a implementação é difícil de explicar, é uma má ideia.
18. Se a implementação é fácil de explicar, pode ser uma boa ideia.
19. Namespaces são uma ideia estupenda — vamos fazer mais desses!

Filosofia aplicada: legível > esperto. Bonito > complexo. Explícito > implícito. Plano > aninhado.

## 1. Zero diagnósticos de Pyright/Pylance — NÃO NEGOCIÁVEL

1. **Qualquer código novo/editado deve ficar sem 0 erros, 0 avisos, 0 informações** no Pyright/Pylance.
2. **Proibido "consertar" com supressão:** `# type: ignore`, `# pyright: ignore`, `# noqa`, `Any` espalhado para silenciar erro é dívida. Só use `# type: ignore[<código>]` com justificativa em comentário e aprovação do usuário.
3. Tipagem obrigatória em assinaturas públicas: parâmetros e retorno. Internos simples podem inferir, mas sem `Any` implícito.
4. Preferir tipos modernos: `str | None` (não `Optional[str]`), `list[int]` (não `List[int]`), `dict[str, Any]`, `X | None = None`.
5. Se o Pyright reclama, o conserto é **tipar direito ou simplificar o código**, nunca esconder.

## 2. Sempre classes, arquivos pequenos

1. **Sempre classes** em arquivos Python (nada de scripts soltos com lógica).
2. **Máximo 200 linhas por arquivo.** Passou disso → modularizar.
3. Arquivo grande → vira pasta com o nome do arquivo, tudo modularizado em módulos pequenos, cada um com sua classe. Exemplo: `store.py` grande → `store/` com `runtime.py`, `json_file.py`, `history.py`, `state.py`, `task_store.py` (+ `__init__.py` re-exportando).
4. Função/método: uma responsabilidade, idealmente ≤ 30 linhas. Erro aninhado demais? Extraia.

## 3. Estrutura de pastas coerente

- `app/` → código principal; `app/services/` → serviços; `app/agent/` → agente.
- `data/mongodb/` → tudo de banco de dados; `data/mongodb/scripts/` → CLIs do banco.
- `data/json/` → runtime JSON de fallback.
- `logs/` → logs centralizados (`.log` ignorados; pasta rastreada com `.gitkeep`).
- `tests/` → suite unitária; `tools/` → CLIs e utilitários.
- Nomes inventados jamais: procurar no projeto antes de criar; preservar interfaces públicas (re-exports finos no `__init__.py` mantêm compatibilidade).
- Git: pastas NUNCA ignoradas; ignorados apenas arquivos de banco/runtime por nome.

## 4. Zen do Python aplicado (boas práticas)

1. **Explícito > implícito:** imports explícitos (`from x import y`, nunca `from x import *`); sem variáveis "mágicas" sem sentido.
2. **Legibilidade conta:** nomes descritivos (`snake_case` para funções/variáveis/módulos, `PascalCase` para classes, `SCREAMING_SNAKE_CASE` para constantes de módulo).
3. **Erros nunca passam silenciosamente:** exceção capturada sem tratamento mínimo precisa de `# pragma: no cover` + justificativa, e nunca engolir `except Exception: pass` escondendo bug real — logue ou documente.
4. **Plano > aninhado:** early return (`if not x: return`) em vez de pirâmide de `if`.
5. **Simplicidade:** não adicionar abstração/dependência sem necessidade real. Uma implementação direta > framework.
6. **Espaço de nomes é uma ideia ótima:** imports no topo do arquivo; import lazy (`from x import y` dentro da função) apenas para quebrar dependência circular ou custo de import — com comentário explicando.
7. **Docstrings** em classes e funções públicas (1–3 linhas dizendo o "porquê/o quê").
8. **Prático vence puro:** compatibilidade Windows/PowerShell em primeiro lugar (encoding UTF-8, caminhos com `os.path`/`pathlib`).

## 5. Consistência entre definições e usos

- Verificar: funções↔chamadas, classes↔importações, argumentos da CLI↔código que os lê, configuração↔uso, rotas↔consumidores, nomes documentados↔implementados.
- Procurar referências a atributos sem definição no parser/construtor.
- Mudou a interface pública? Atualize todos os consumidores + re-export no `__init__.py`.

## 6. Testes acompanham o código

1. Todo comportamento novo/corrigido tem teste mínimo (não artificial).
2. Testes usam fallback JSON com caminhos temporários (não tocam no MongoDB real).
3. Suite tem que passar 100% antes de declarar pronto.
4. quando encontrar um problema antes de alterar algo me pergunte
5. explique o problema
## 7. Checklist de entrega (antes de "pronto")

```bash
python -m compileall -q app data/mongodb main.py tools tests
python -m unittest discover -s tests -v
pyright app data project_path tools tests   # 0 erros, 0 avisos, 0 infos
python tools/validate.py
git diff --check
```
## 8. liguagem defalt do usuario
PT-BR Portuges Brazil

Se qualquer item falha, **não está pronto**. Corrija a causa, não o sintoma.