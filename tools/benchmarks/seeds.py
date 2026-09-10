import os

from tools.benchmarks.tasks.core import BenchmarkTask


SeedFiles = dict[str, str]


class BenchmarkProjectSeeder:
    """Cria os arquivos iniciais específicos de cada tarefa do benchmark."""

    SEEDS: dict[str, SeedFiles] = {
        "002_editar_funcao": {"calc.py": "def add(a, b):\n    return a + b\n"},
        "004_bug_multi_arquivo": {
            "src/app.py": "from src.utils.helpers import needed\n\n\ndef main():\n    return needed()\n"
        },
        "005_feature_com_testes": {
            "string_utils.py": "def slugify(text):\n    return text  # TODO: implementar\n"
        },
        "006_refactor_sem_quebrar": {"calc.py": "def add(a, b):\n    return a + b\n"},
        "007_interpretar_erro": {
            "main.py": "from calc import add\n\nprint(add(1, 2))\n"
        },
        "009_codigo_e_docs": {"calc.py": "def add(a, b):\n    return a + b\n"},
        "008_projeto_desconhecido": {
            "src/app.py": "from src.core import process\n\ndef main():\n    return process()\n"
        },
        "010_consertar_incompleto": {
            "calc.py": "def add(a, b, c)\n    return a + b + c\n"
        },
    }

    def seed(self, task: BenchmarkTask, project_dir: str) -> None:
        for relative, content in self.SEEDS.get(task.task_id, {}).items():
            path = os.path.join(project_dir, relative)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as stream:
                stream.write(content)
