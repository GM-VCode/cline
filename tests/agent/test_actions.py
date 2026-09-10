# ============================================================
#  tests/test_actions.py — ActionLoop (etapa 11c, sem modelo)
# ============================================================

import os
import sys
import tempfile
import unittest
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

from app.agent.checks import CheckRunner            # noqa: E402
from app.agent.runner.actions import ActionLoop     # noqa: E402
from app.agent.runner.core import AgentRunner       # noqa: E402


class StepExec:
    """Executor fake que devolve passos de uma fila."""

    def __init__(self, steps: list[dict[str, Any]]) -> None:
        self.steps = list(steps)
        self.histories: list[list[dict[str, str]]] = []

    def execute_action(self, prompt: str, project_dir: str,
                       history: list[dict[str, str]],
                       ) -> dict[str, Any] | None:
        _ = prompt, project_dir
        self.histories.append(list(history))
        return self.steps.pop(0) if self.steps else {"action": "done"}

    # ExecutorProtocol (core.py): AgentRunner exige os 3 métodos
    def execute(self, instruction: str, /,
                project_dir: str) -> dict[str, Any]:
        _ = instruction, project_dir
        return {"action": "done"}

    def execute_with_feedback(self, instruction: str, /,
                              project_dir: str,
                              feedback: str) -> dict[str, Any]:
        _ = instruction, project_dir, feedback
        return {"action": "done"}


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

    def test_edit_achatado_aplica(self):
        """Modelo manda file/find/replace no nível da ação (bug da prova real)."""
        ex = StepExec([
            {"action": "edit", "file": "calc.py",
             "find": "return a - b", "replace": "return a + b"},
            {"action": "done"},
        ])
        r = ActionLoop(ex, self.checks, self.dir, check_cmd=[]).run("x")
        self.assertTrue(r["finished"])
        with open(os.path.join(self.dir, "calc.py"), encoding="utf-8") as fh:
            self.assertIn("return a + b", fh.read())

    def test_edit_vazio_nao_mentira_ok(self):
        ex = StepExec([
            {"action": "edit"},
            {"action": "done"},
        ])
        r = ActionLoop(ex, self.checks, self.dir, check_cmd=[]).run("x")
        self.assertTrue(r["finished"])
        self.assertIn("nada foi modificado",
                      ex.histories[1][0]["observation"])


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
        # ciclo antigo: settle() sem check_cmd, edits_failed nem run → ok.
        # (antes este teste passava por AttributeError do fake sem
        # 'execute' — erro silencioso; agora o fake implementa o
        # protocolo completo, como o ExecutorProtocol exige)
        self.assertTrue(r["finished"])
        self.assertNotIn("actions_used", r)


if __name__ == "__main__":
    unittest.main()
