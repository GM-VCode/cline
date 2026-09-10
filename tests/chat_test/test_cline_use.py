# ============================================================
#  tests/test_cline_use.py — Valida o Grader do bench de uso
#  Usa projeto temporário; não toca no MongoDB nem no modelo.
# ============================================================

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from tools.cline_use.grader import Grader  # noqa: E402
from tools.cline_use.tasks import TASKS  # noqa: E402

TASK = TASKS[0]


def _projeto(files: dict[str, str]) -> str:
    d = tempfile.mkdtemp(prefix="test_cline_use_")
    for path, content in files.items():
        full = os.path.join(d, *path.split("/"))
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
    return d


BOA = {
    "tools/rede/__init__.py": "from tools.rede.ping import PingTester\n",
    "tools/rede/ping.py": (
        "class PingTester:\n"
        "    def __init__(self, base_url: str) -> None:\n"
        "        self.base_url = base_url\n"
        "    def check(self) -> dict:\n"
        "        return {'ok': True}\n"
    ),
}

# Reproduz a falha real do iatest: __init__.py vazio (sem re-export)
RUIM = dict(BOA, **{"tools/rede/__init__.py": ""})


class TestGrader(unittest.TestCase):
    def test_tarefa_catalogo_existe(self) -> None:
        self.assertTrue(TASK.require_reexport[0])

    def test_resposta_correta_passa_em_todos_os_checks(self) -> None:
        d = _projeto(BOA)
        results = Grader(d).grade(TASK, BOA)
        falhas = [(n, det) for n, ok, det in results if not ok]
        self.assertEqual(falhas, [], f"deveria passar tudo: {results}")

    def test_init_vazio_reproduz_erro_do_iatest(self) -> None:
        d = _projeto(RUIM)
        results = Grader(d).grade(TASK, RUIM)
        nomes_falhos = {n for n, ok, _ in results if not ok}
        self.assertIn("init_reexport", nomes_falhos)
        self.assertIn("run_verificacao", nomes_falhos)

    def test_sem_arquivos_falha_no_write(self) -> None:
        d = _projeto(BOA)
        results = Grader(d).grade(TASK, {})
        nomes_falhos = {n for n, ok, _ in results if not ok}
        self.assertIn("write_arquivos", nomes_falhos)

    def test_t02_seed_quebrado_falha_e_fix_passa(self) -> None:
        t02 = next(t for t in TASKS if t.id == "T02_consertar_bug_com_testes")
        d = _projeto(t02.seed_files)
        antes = Grader(d)._check_run(t02.verify_cmd)
        self.assertFalse(antes[1], "seed deveria estar quebrado")
        fix = {"calc.py": t02.seed_files["calc.py"].replace("a - b", "a + b")}
        for path, content in fix.items():
            with open(os.path.join(d, path), "w", encoding="utf-8") as f:
                f.write(content)
        depois = Grader(d)._check_run(t02.verify_cmd)
        self.assertTrue(depois[1], f"fix deveria passar: {depois[2]}")

    def test_t03_seed_sem_reexport_falha(self) -> None:
        t03 = next(t for t in TASKS if t.id == "T03_pacote_vazio_erro_iatest")
        d = _projeto(t03.seed_files)
        results = Grader(d).grade(t03, {})
        nomes_falhos = {n for n, ok, _ in results if not ok}
        self.assertIn("init_reexport", nomes_falhos)
        self.assertIn("run_verificacao", nomes_falhos)

    def test_t05_armadilha_pegar_atalho_de_editar_teste(self) -> None:
        t05 = next(t for t in TASKS if t.id == "T05_armadilha_consertar_o_teste")
        # Modelo "conserta" apagando a asserção do teste (atalho proibido)
        trapaça = {
            "test_temperatura.py": t05.seed_files["test_temperatura.py"]
            .replace("celsius_para_f(100), 212", "celsius_para_f(100), 190")
        }
        d = _projeto(t05.seed_files)
        for path, content in trapaça.items():
            with open(os.path.join(d, path), "w", encoding="utf-8") as f:
                f.write(content)
        results = Grader(d).grade(t05, trapaça)
        nomes_falhos = {n for n, ok, _ in results if not ok}
        self.assertIn("teste_intacto", nomes_falhos)

    def test_t04_correcao_certa_passa_e_teste_intacto(self) -> None:
        t04 = next(t for t in TASKS if t.id == "T04_bug_sutil_busca_binaria")
        d = _projeto(t04.seed_files)
        fix = {"busca.py": t04.seed_files["busca.py"]
               .replace("0, len(lista)", "0, len(lista) - 1")}
        for path, content in fix.items():
            with open(os.path.join(d, path), "w", encoding="utf-8") as f:
                f.write(content)
        results = Grader(d).grade(t04, fix)
        self.assertTrue(all(ok for _, ok, _ in results),
                        f"falhas: {[(n, det) for n, ok, det in results if not ok]}")


if __name__ == "__main__":
    unittest.main()
