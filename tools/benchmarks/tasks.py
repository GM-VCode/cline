# ============================================================
#  benchmarks/tasks.py — class BenchmarkTask + catálogo
#  Tarefas padronizadas para medir a qualidade do modelo como
#  programador. Cada tarefa define: id, categoria, instrução,
#  arquivos esperados no resultado e como validar.
# ============================================================

import os


class BenchmarkTask:
    """Uma tarefa padronizada do benchmark."""

    def __init__(self, task_id: str, category: str, instruction: str,
                 expected_files: list, checks: list):
        self.task_id = task_id
        self.category = category          # bug | feature | refactor | docs
        self.instruction = instruction    # prompt enviado ao modelo
        self.expected_files = expected_files
        self.checks = checks              # lista de (nome, callable)->(ok,msg)

    def run_checks(self, project_dir: str) -> list:
        """Executa os checks da tarefa; retorna [(check, ok, msg)]."""
        out = []
        for name, fn in self.checks:
            try:
                ok, msg = fn(project_dir)
            except Exception as exc:  # pragma: no cover
                ok, msg = False, f"exceção no check {name}: {exc}"
            out.append((name, ok, msg))
        return out


def _file_contains(rel_path: str, needle: str):
    """Fábrica de check: arquivo existe e contém `needle`."""
    def check(project_dir: str):
        path = os.path.join(project_dir, rel_path)
        if not os.path.isfile(path):
            return False, f"arquivo ausente: {rel_path}"
        with open(path, "r", encoding="utf-8") as f:
            if needle in f.read():
                return True, f"{rel_path} contém '{needle}'"
        return False, f"{rel_path} não contém '{needle}'"
    return check


def _file_exists(rel_path: str):
    def check(project_dir: str):
        exists = os.path.isfile(os.path.join(project_dir, rel_path))
        return exists, f"{rel_path} {'existe' if exists else 'ausente'}"
    return check


import os  # noqa: E402  (usado pelos checks acima)


def default_catalog() -> list:
    """Catálogo padrão de 10 tarefas padronizadas do benchmark."""
    return [
        BenchmarkTask(
            "001_criar_funcao", "feature",
            "Crie calc.py com uma função add(a, b) que retorna a soma.",
            ["calc.py"],
            [("existe", _file_exists("calc.py")),
             ("contem_add", _file_contains("calc.py", "def add")),
             ("contem_return", _file_contains("calc.py", "return"))],
        ),
        BenchmarkTask(
            "002_editar_funcao", "feature",
            "Edite calc.py: mude add(a, b) para aceitar um terceiro "
            "parâmetro c e somar os três.",
            ["calc.py"],
            [("contem_3_params", _file_contains("calc.py", "def add(a, b, c)"))],
        ),
        BenchmarkTask(
            "003_bug_simples", "bug",
            "Em calc.py a função div(a, b) faz a/b errado: use "
            "divisão correta. Corrija e garanta que a função existe.",
            ["calc.py"],
            [("contem_div", _file_contains("calc.py", "def div")),
             ("contem_slash", _file_contains("calc.py", "/"))],
        ),
        BenchmarkTask(
            "004_bug_multi_arquivo", "bug",
            "O projeto tem src/app.py importando de src/utils/helpers.py "
            "que não existe. Crie helpers.py com a função usada.",
            ["src/app.py", "src/utils/helpers.py"],
            [("app_existe", _file_exists("src/app.py")),
             ("helpers_existe", _file_exists("src/utils/helpers.py"))],
        ),
        BenchmarkTask(
            "005_feature_com_testes", "feature",
            "Crie string_utils.py com a função slugify(text) e "
            "test_string_utils.py com ao menos um teste de unittest.",
            ["string_utils.py", "test_string_utils.py"],
            [("mod_existe", _file_exists("string_utils.py")),
             ("teste_existe", _file_exists("test_string_utils.py")),
             ("usa_unittest", _file_contains("test_string_utils.py", "unittest"))],
        ),
        BenchmarkTask(
            "006_refactor_sem_quebrar", "refactor",
            "Refatore calc.py: extraia a soma para uma função interna "
            "_sum(a, b, c) mantendo add(a, b, c) pública.",
            ["calc.py"],
            [("add_publica", _file_contains("calc.py", "def add(a, b, c)")),
             ("sum_interna", _file_contains("calc.py", "def _sum"))],
        ),
        BenchmarkTask(
            "007_interpretar_erro", "bug",
            "Rodar python -m unittest deu 'ModuleNotFoundError: calc'. "
            "Diagnostique e corrija (crie o módulo que falta).",
            ["calc.py"],
            [("calc_existe", _file_exists("calc.py"))],
        ),
        BenchmarkTask(
            "008_projeto_desconhecido", "bug",
            "Este projeto tem src/app.py quebrado. Encontre o problema, "
            "corrija e mantenha a estrutura.",
            ["src/app.py"],
            [("app_existe", _file_exists("src/app.py"))],
        ),
        BenchmarkTask(
            "009_codigo_e_docs", "docs",
            "Crie README.md documentando como usar calc.py (função add).",
            ["README.md", "calc.py"],
            [("readme_existe", _file_exists("README.md")),
             ("docs_citam_add", _file_contains("README.md", "add"))],
        ),
        BenchmarkTask(
            "010_consertar_incompleto", "bug",
            "Alguém começou a editar calc.py e deixou pela metade "
            "(syntax quebrada). Conserte o arquivo completo.",
            ["calc.py"],
            [("add_existe", _file_contains("calc.py", "def add"))],
        ),
    ]