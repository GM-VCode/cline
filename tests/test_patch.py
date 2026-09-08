# ============================================================
#  tests/test_patch.py — PatchApplier (etapa 11b) e integração
#  de "edits" no AgentRunner (sem modelo, executor fake).
# ============================================================

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.apply import PatchApplier            # noqa: E402
from app.agent.runner import AgentRunner            # noqa: E402
from tests.test_agent import FakeExecutor           # noqa: E402


class TestPatchApplier(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "grande.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("def a():\n    return 1\n\n\ndef b():\n    return 2\n\n\n"
                     "def c():\n    return 3\n")

    def _read(self, name="grande.py"):
        with open(os.path.join(self.dir, name), encoding="utf-8") as fh:
            return fh.read()

    def test_patch_aplicado_troca_so_o_trecho(self):
        ok, rep = PatchApplier().apply(self.dir, [{
            "file": "grande.py", "find": "return 2", "replace": "return 20"}])
        self.assertTrue(ok, rep)
        self.assertIn("return 20", self._read())
        self.assertIn("return 1", self._read())   # resto intacto
        self.assertIn("return 3", self._read())

    def test_find_ambiguo_rejeita_sem_escrever(self):
        antes = self._read()
        ok2, rep2 = PatchApplier().apply(self.dir, [{
            "file": "grande.py", "find": "    return",
            "replace": "x"}])
        self.assertFalse(ok2)
        self.assertIn("ambíguo", rep2[0])
        self.assertEqual(antes, self._read())  # nada mudou

    def test_find_inexistente_rejeita_e_mostra_conteudo(self):
        ok, rep = PatchApplier().apply(self.dir, [{
            "file": "grande.py", "find": "NAO_EXISTE_123",
            "replace": "x"}])
        self.assertFalse(ok)
        self.assertIn("não encontrado", rep[0])
        self.assertIn("def a()", rep[0])  # trecho real vem no erro

    def test_arquivo_inexistente_pedindo_files(self):
        ok, rep = PatchApplier().apply(self.dir, [{
            "file": "novo.py", "find": "a", "replace": "b"}])
        self.assertFalse(ok)
        self.assertIn("use 'files'", rep[0])
        self.assertFalse(os.path.exists(os.path.join(self.dir, "novo.py")))

    def test_caminho_fora_do_projeto_rejeitado(self):
        ok, rep = PatchApplier().apply(self.dir, [{
            "file": "../fora.py", "find": "a", "replace": "b"}])
        self.assertFalse(ok)
        self.assertIn("fora do projeto", rep[0])

    def test_edit_nao_dict_ou_incompleto(self):
        ok, rep = PatchApplier().apply(self.dir, ["x"])
        self.assertFalse(ok)
        ok, rep = PatchApplier().apply(
            self.dir, [{"file": "grande.py", "find": "return 1"}])
        self.assertFalse(ok)
        self.assertIn("obrigatórios", rep[0])


class TestAgentRunnerEdits(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "calc.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("def add(a, b):\n    return a - b\n")
        self.check = [sys.executable, "-c",
                      "import calc; assert calc.add(2, 3) == 5"]

    def test_edits_bons_aplicados_e_verificados(self):
        class Editor(FakeExecutor):
            def execute(self, instruction, project_dir):
                return {"tool_calls": 1, "retries": 0, "tokens": 0,
                        "files_written": [], "files": {},
                        "edits_applied": ["editado: calc.py"],
                        "run": None}

        r = AgentRunner(Editor(), check_cmd=self.check).run("x", self.dir)
        self.assertTrue(r["finished"])
        with open(os.path.join(self.dir, "calc.py"), encoding="utf-8") as fh:
            self.assertIn("a + b", fh.read())

    def test_edits_ruins_viram_feedback(self):
        class Ruim(FakeExecutor):
            def __init__(self):
                super().__init__(bug_antes=False)
                self.feedbacks = []

            def execute(self, instruction, project_dir):
                return {"tool_calls": 0, "retries": 0, "tokens": 0,
                        "files_written": [], "files": {},
                        "edits_failed": True,
                        "edit_errors": ["edit[0]: 'find' não encontrado"],
                        "run": None}

            def execute_with_feedback(self, i, p, fb):
                self.feedbacks.append(fb)
                return self.execute(i, p)

        ex = Ruim()
        r = AgentRunner(ex, check_cmd=self.check,
                        max_attempts=1).run("x", self.dir)
        self.assertFalse(r["finished"])
        self.assertIn("REJEITADAS", r["error"])


if __name__ == "__main__":
    unittest.main()
