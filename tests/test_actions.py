# ============================================================
#  tests/test_actions.py — ActionLoop (etapa 11c, sem modelo)
# ============================================================

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agent.checks import CheckRunner            # noqa: E402
from app.agent.runner.actions import ActionLoop     # noqa: E402
from app.agent.runner.core import AgentRunner       # noqa: E402


class StepExec:
    """Executor fake que devolve passos de uma fila."""

    def __init__(self, steps):
        self.steps = list(steps)
        self.histories = []

    def execute_action(self, prompt, project_dir, history):
        self.histories.append(list(history))
        return self.steps.pop(0) if self.steps else {"action": "done"}


class TestActionLoop(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        with open(os.path.join(self.dir, "calc.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("def add(a, b):\n    return a - b\n")
        self.checks = CheckRunner(timeout=30)
        self.check = [sys.executable, "-c",
                      "import calc; assert calc.add(2, 3) == 5"]

    def test_sequencia_edit_run_done(self):
        ex = StepExec([
            {"action": "edit", "edits": [
                {"file": "calc.py", "find": "return a - b",
                 "replace": "return a + b"}]},
            {"action": "run", "cmd": f"{sys.executable} -c "
                                     "\"import calc; print(calc.add(2,3))\""},
            {"action": "done", "note": "conferido"},
        ])
        r = ActionLoop(ex, self.checks, self.dir,
                       check_cmd=self.check).run("x")
        self.assertTrue(r["finished"])
        self.assertEqual(r["actions_used"], 2)   # done não conta
        self.assertEqual(r["internal_runs"], 1)
        with open(os.path.join(self.dir, "calc.py"), encoding="utf-8") as fh:
            self.assertIn("return a + b", fh.read())
        # histórico chega ao executor (observação do run visível)
        self.assertEqual(len(ex.histories[2]), 2)

    def test_orcamento_estourado(self):
        ex = StepExec([{"action": "run", "cmd": "echo passo"}] * 10)
        r = ActionLoop(ex, self.checks, self.dir, max_actions=3).run("x")
        self.assertFalse(r["finished"])
        self.assertIn("esgotado", r["error"])
        self.assertEqual(r["actions_used"], 3)

    def test_acao_invalida_vira_observacao(self):
        ex = StepExec([
            {"action": "voar", "note": "??"},
            {"action": "done"},
        ])
        r = ActionLoop(ex, self.checks, self.dir,
                       check_cmd=[]).run("x")
        self.assertTrue(r["finished"])
        obs = ex.histories[1][0]["observation"]
        self.assertIn("Ação inválida", obs)

    def test_done_sem_check_passa_direto(self):
        ex = StepExec([{"action": "done"}])
        r = ActionLoop(ex, self.checks, self.dir, check_cmd=[]).run("x")
        self.assertTrue(r["finished"])

    def test_done_com_check_falho_nao_passa(self):
        ex = StepExec([{"action": "done"}])
        bad = [sys.executable, "-c", "import sys; sys.exit(3)"]
        r = ActionLoop(ex, self.checks, self.dir, check_cmd=bad).run("x")
        self.assertFalse(r["finished"])

    def test_write_cria_arquivo(self):
        ex = StepExec([
            {"action": "write", "files": {"novo.py": "x = 1\n"}},
            {"action": "done"},
        ])
        r = ActionLoop(ex, self.checks, self.dir, check_cmd=[]).run("x")
        self.assertTrue(r["finished"])
        self.assertEqual(r["files_written"], ["novo.py"])
        self.assertTrue(os.path.exists(os.path.join(self.dir, "novo.py")))


class TestRunnerMaxActions(unittest.TestCase):
    def test_max_actions_ativa_modo_iterativo(self):
        dir_ = tempfile.mkdtemp()
        ex = StepExec([{"action": "done"}])
        r = AgentRunner(ex, check_cmd=[], max_actions=5).run("x", dir_)
        self.assertTrue(r["finished"])
        self.assertIn("actions_used", r)

    def test_sem_max_actions_mantem_ciclo_antigo(self):
        dir_ = tempfile.mkdtemp()
        ex = StepExec([{"action": "done"}])
        r = AgentRunner(ex, check_cmd=[]).run("x", dir_)
        self.assertFalse(r["finished"])   # executor antigo: sem files → falha
        self.assertNotIn("actions_used", r)


if __name__ == "__main__":
    unittest.main()
