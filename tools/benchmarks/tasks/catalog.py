# ============================================================
#  tools/benchmarks/tasks/catalog.py — catálogo padrão
#  10 tarefas originais + 005X (variante longa de feature com
#  testes, que valida comportamento real com unittest/expr).
# ============================================================

from tools.benchmarks.tasks.checks import (
    file_contains, file_exists)
from tools.benchmarks.tasks.core import BenchmarkTask
from tools.benchmarks.tasks.task_005x import feature_com_testes_longa


def default_catalog() -> list[BenchmarkTask]:
    """Catálogo padrão de 11 tarefas padronizadas do benchmark."""
    return [
        BenchmarkTask(
            "001_criar_funcao", "feature",
            "Crie calc.py com uma função add(a, b) que retorna a soma.",
            ["calc.py"],
            [("existe", file_exists("calc.py")),
             ("contem_add", file_contains("calc.py", "def add")),
             ("contem_return", file_contains("calc.py", "return"))],
        ),
        BenchmarkTask(
            "002_editar_funcao", "feature",
            "Edite calc.py: mude add(a, b) para aceitar um terceiro "
            "parâmetro c e somar os três.",
            ["calc.py"],
            [("contem_3_params",
              file_contains("calc.py", "def add(a, b, c"))],
        ),
        BenchmarkTask(
            "003_bug_simples", "bug",
            "Em calc.py a função div(a, b) faz a/b errado: use "
            "divisão correta. Corrija e garanta que a função existe.",
            ["calc.py"],
            [("contem_div", file_contains("calc.py", "def div")),
             ("contem_slash", file_contains("calc.py", "/"))],
        ),
        BenchmarkTask(
            "004_bug_multi_arquivo", "bug",
            "O projeto tem src/app.py importando needed() de "
            "src/utils/helpers.py que não existe. Crie "
            "src/utils/helpers.py com a função needed().",
            ["src/app.py", "src/utils/helpers.py"],
            [("app_existe", file_exists("src/app.py")),
             ("helpers_existe", file_exists("src/utils/helpers.py"))],
        ),
        feature_com_testes_longa(),
        BenchmarkTask(
            "005_feature_com_testes", "feature",
            "Crie DOIS arquivos: (1) string_utils.py com a função "
            "slugify(text) implementada; (2) test_string_utils.py com "
            "ao menos um teste usando unittest. Ambos na raiz do projeto.",
            ["string_utils.py", "test_string_utils.py"],
            [("mod_existe", file_exists("string_utils.py")),
             ("teste_existe", file_exists("test_string_utils.py")),
             ("usa_unittest", file_contains("test_string_utils.py",
                                            "unittest"))],
        ),
        BenchmarkTask(
            "006_refactor_sem_quebrar", "refactor",
            "Refatore calc.py: extraia a soma para uma função interna "
            "_sum(a, b, c) mantendo add(a, b, c) pública.",
            ["calc.py"],
            [("add_publica", file_contains("calc.py", "def add(a, b, c")),
             ("sum_interna", file_contains("calc.py", "def _sum"))],
        ),
        BenchmarkTask(
            "007_interpretar_erro", "bug",
            "Rodar python main.py deu 'ModuleNotFoundError: No module "
            "named calc'. Diagnostique e corrija criando o arquivo "
            "calc.py na raiz, com a função add(a, b).",
            ["calc.py"],
            [("calc_existe", file_exists("calc.py"))],
        ),
        BenchmarkTask(
            "008_projeto_desconhecido", "bug",
            "Este projeto tem src/app.py quebrado. Encontre o problema, "
            "corrija e mantenha a estrutura.",
            ["src/app.py"],
            [("app_existe", file_exists("src/app.py"))],
        ),
        BenchmarkTask(
            "009_codigo_e_docs", "docs",
            "Crie README.md documentando como usar calc.py (função add).",
            ["README.md", "calc.py"],
            [("readme_existe", file_exists("README.md")),
             ("docs_citam_add", file_contains("README.md", "add"))],
        ),
        BenchmarkTask(
            "010_consertar_incompleto", "bug",
            "Alguém começou a editar calc.py e deixou pela metade "
            "(syntax quebrada). Conserte o arquivo completo.",
            ["calc.py"],
            [("add_existe", file_contains("calc.py", "def add"))],
        ),
    ]
