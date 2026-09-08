# ============================================================
#  tests/test_agent.py — tests do agente real (app/agent)
#  Executor fake: sem VRAM, sem rede. Cenários: sucesso de
#  primeira, recuperação via retry com feedback, falha final,
#  projeto inexistente e CheckRunner isolado.
# ============================================================

import os
import shutil
import sys
import tempfile
import unittest

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

# higiene: tests do agente NÃO poluem logs/agent.log real
os.environ["AGENT_LOG_PATH"] = os.path.join(tempfile.gettempdir(),
                                            "agent_test.log")

from app.agent import AgentRunner, CheckRunner    # noqa: E402


class FakeExecutor:
    """Escreve calc.py com ou sem bug, dependendo do modo."""

    def __init__(self, bug_antes=True):
        self.bug_antes = bug_antes
        self.feedbacks = []

    def _write(self, project_dir, com_bug):
        path = os.path.join(project_dir, "calc.py")
        corpo = ("def add(a, b):\n"
                 "    return a - b if %r else a + b\n" % com_bug)
        with open(path, "w", encoding="utf-8") as f:
            f.write(corpo)
        return {"files_written": ["calc.py"], "tokens": 10}

    def execute(self, instruction, project_dir):
        return self._write(project_dir, self.bug_antes)

    def execute_with_feedback(self, instruction, project_dir, feedback):
        self.feedbacks.append(feedback)
        return self._write(project_dir, False)


class TestAgentRunner(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="agent_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.check = [sys.executable, "-c",
                      "import calc; assert calc.add(2, 3) == 5"]

    def test_sucesso_de_primeira(self):
        runner = AgentRunner(FakeExecutor(bug_antes=False),
                             check_cmd=self.check)
        r = runner.run("conserte add", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["attempts"], 1)
        self.assertEqual(r["retries"], 0)

    def test_retry_com_feedback_recupera(self):
        ex = FakeExecutor(bug_antes=True)
        runner = AgentRunner(ex, check_cmd=self.check, max_attempts=2)
        r = runner.run("conserte add", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["attempts"], 2)
        self.assertEqual(r["retries"], 1)
        self.assertIn("não passou na verificação", ex.feedbacks[0])
        self.assertIn("Saída da verificação", ex.feedbacks[0])

    def test_falha_final_quando_check_nunca_passa(self):
        class Ruim(FakeExecutor):
            def _write(self, project_dir, com_bug):
                return self._write_sempre_ruim(project_dir)

            def _write_sempre_ruim(self, project_dir):
                path = os.path.join(project_dir, "calc.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("def add(a, b):\n    return a - b\n")
                return {"files_written": ["calc.py"]}

        runner = AgentRunner(Ruim(), check_cmd=self.check, max_attempts=2)
        r = runner.run("conserte add", self.dir)
        self.assertFalse(r["finished"])
        self.assertEqual(r["attempts"], 2)
        self.assertEqual(r["retries"], 1)

    def test_projeto_inexistente_falha_sem_lancar(self):
        runner = AgentRunner(FakeExecutor(), check_cmd=self.check)
        r = runner.run("x", os.path.join(self.dir, "não_existe"))
        self.assertFalse(r["finished"])
        self.assertIn("não existe", r["error"])

    def test_sem_check_cmd_passa_direto(self):
        runner = AgentRunner(FakeExecutor(bug_antes=True))
        r = runner.run("x", self.dir)
        self.assertTrue(r["finished"])

    def test_store_registra_execucao(self):
        class FakeStore:
            def __init__(self):
                self.entries = []

            def append_agent_run(self, entry, task_id=None):
                self.entries.append(entry)
                return entry

            def save_state(self, payload, task_id=None):
                return payload

        store = FakeStore()
        runner = AgentRunner(FakeExecutor(bug_antes=False),
                             check_cmd=self.check, store=store)
        runner.run("conserte add", self.dir)
        self.assertEqual(len(store.entries), 1)
        e = store.entries[0]
        self.assertTrue(e["finished"])
        self.assertEqual(e["files"], ["calc.py"])

    def test_sem_store_nao_registra_nada(self):
        runner = AgentRunner(FakeExecutor(bug_antes=False),
                             check_cmd=self.check, store=None)
        r = runner.run("x", self.dir)  # não deve lançar
        self.assertTrue(r["finished"])

    def test_run_interno_do_modelo_passa(self):
        class ComRun(FakeExecutor):
            def execute(self, instruction, project_dir):
                r = self._write(project_dir, False)
                r["run"] = "python -c \"print('validado')\""
                return r

        runner = AgentRunner(ComRun(), check_cmd=self.check)
        r = runner.run("x", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["internal_runs"], 1)

    def test_run_interno_falho_vira_feedback_e_retry(self):
        class RunRuim(FakeExecutor):
            def __init__(self):
                super().__init__(bug_antes=True)
                self.chamadas = 0

            def _respond(self, project_dir):
                self.chamadas += 1
                com_bug = self.chamadas == 1
                r = self._write(project_dir, com_bug)
                r["run"] = "python -c \"import calc; assert calc.add(2, 3) == 5\""
                return r

            def execute(self, instruction, project_dir):
                return self._respond(project_dir)

            def execute_with_feedback(self, instruction, project_dir,
                                      feedback):
                self.feedbacks.append(feedback)
                return self._respond(project_dir)

        ex = RunRuim()
        runner = AgentRunner(ex, check_cmd=self.check, max_attempts=2)
        r = runner.run("conserte add", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["internal_runs"], 2)
        self.assertIn("que você pediu para executar", ex.feedbacks[0])

    def test_run_interno_invalido_nao_lanca(self):
        class RunLouco(FakeExecutor):
            def execute(self, instruction, project_dir):
                r = self._write(project_dir, False)
                r["run"] = "comando_que_nao_existe_12345"
                return r

        runner = AgentRunner(RunLouco(), check_cmd=[], max_attempts=1)
        r = runner.run("x", self.dir)
        self.assertFalse(r["finished"])
        self.assertIn("que você pediu para executar", r["error"])


class TestCheckRunner(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="check_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_cmd_ok(self):
        ok, out = CheckRunner().run(
            [sys.executable, "-c", "print('oi')"], self.dir)
        self.assertTrue(ok)
        self.assertIn("oi", out)

    def test_cmd_com_erro(self):
        ok, out = CheckRunner().run([sys.executable, "-c", "exit(3)"], self.dir)
        self.assertFalse(ok)

    def test_cmd_inexistente_nao_lanca(self):
        ok, out = CheckRunner(timeout=5).run(
            ["definitivamente_nao_existe_cmd"], self.dir)
        self.assertFalse(ok)
        self.assertIn("erro ao executar check", out)


if __name__ == "__main__":
    unittest.main()
