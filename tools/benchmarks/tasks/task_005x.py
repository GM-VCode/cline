# ============================================================
#  tools/benchmarks/tasks/task_005x.py — tarefa longa
#  Variante estendida de "feature com testes": 3 funções +
#  unittest real + checks de comportamento (executa o código).
# ============================================================

from tools.benchmarks.tasks.checks import (
    file_contains, file_exists, python_expr_ok, unittest_ok)
from tools.benchmarks.tasks.core import BenchmarkTask


def feature_com_testes_longa() -> BenchmarkTask:
    """005X: feature multi-função com testes que RODAM de verdade."""
    return BenchmarkTask(
        "005X_feature_com_testes_longa", "feature",
        "Crie DOIS arquivos com implementação REAL e completa:\n"
        "(1) string_utils.py na raiz, contendo:\n"
        "    - def slugify(text): converte para slug minúsculo "
        "(acentos removidos, espaços e pontuação viram hífen, "
        "hífens já existentes contam como separador e NÃO duplicam, "
        "sem hífens duplos e sem hífens nas pontas);\n"
        "    - def truncate(text, limit): corta o texto em `limit` "
        "caracteres adicionando '...' quando cortar (nunca passando "
        "de limit+3 caracteres);\n"
        "    - def camel_to_snake(name): converte CamelCase para "
        "snake_case.\n"
        "(2) test_string_utils.py na raiz, com classe "
        "TestStringUtils(unittest.TestCase) e AO MENOS UM método de "
        "teste para CADA função (slugify, truncate, camel_to_snake), "
        "incluindo um caso com acentuação (ex.: 'Ação' → 'acao').\n"
        "Use apenas a biblioteca padrão (unittest, unicodedata).",
        ["string_utils.py", "test_string_utils.py"],
        [("mod_existe", file_exists("string_utils.py")),
         ("teste_existe", file_exists("test_string_utils.py")),
         ("usa_unittest", file_contains("test_string_utils.py",
                                        "unittest")),
         ("tem_slugify", file_contains("string_utils.py",
                                       "def slugify")),
         ("tem_truncate", file_contains("string_utils.py",
                                        "def truncate")),
         ("tem_camel", file_contains("string_utils.py",
                                     "def camel_to_snake")),
         ("teste_slugify", file_contains("test_string_utils.py",
                                         "slugify")),
         ("teste_camel", file_contains("test_string_utils.py",
                                       "camel_to_snake")),
         ("testes_passam", unittest_ok("test_string_utils.py")),
         ("slugify_acentos", python_expr_ok(
             "string_utils",
             "slugify('Ação é gru-nto') == 'acao-e-gru-nto'")),
         ("truncate_corta", python_expr_ok(
             "string_utils",
             "truncate('abcdefghij', 5) == 'abcde...'")),
         ("camel_converte", python_expr_ok(
             "string_utils",
             "camel_to_snake('MinhaClasseLegal') "
             "== 'minha_classe_legal'")),
        ],
    )
