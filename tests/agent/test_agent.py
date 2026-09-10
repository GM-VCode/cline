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
from typing import Any

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

# higiene: tests do agente NÃO poluem logs/agent.log real
os.environ["AGENT_LOG_PATH"] = os.path.join(tempfile.gettempdir(),
                                            "agent_test.log")

from app.agent import AgentRunner, CheckRunner    # noqa: E402


class FakeExecutor:
    """Escreve calc.py com ou sem bug, dependendo do modo."""

    def __init__(self, bug_antes: bool = True) -> None:
        self.bug_antes = bug_antes
        self.feedbacks: list[str] = []

    def _write(self, project_dir: str, com_bug: bool) -> dict[str, Any]:
        path = os.path.join(project_dir, "calc.py")
        corpo = ("def add(a, b):\n"
                 "    return a - b if %r else a + b\n" % com_bug)
        with open(path, "w", encoding="utf-8") as f:
            f.write(corpo)
        return {"files_written": ["calc.py"], "tokens": 10}

    def execute(self, prompt: str, project_dir: str) -> dict[str, Any]:
        _ = prompt
        return self._write(project_dir, self.bug_antes)

    def execute_with_feedback(
        self,
        prompt: str,
        project_dir: str,
        feedback: str,
    ) -> dict[str, Any]:
        _ = prompt
        self.feedbacks.append(feedback)
        return self._write(project_dir, False)

    def execute_action(
        self,
        prompt: str,
        project_dir: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        _ = history
        return self.execute(prompt, project_dir)


class TestAgentRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="agent_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.check: list[str] = [
            sys.executable,
            "-c",
            "import calc; assert calc.add(2, 3) == 5",
        ]

    def test_sucesso_de_primeira(self) -> None:
        runner = AgentRunner(FakeExecutor(bug_antes=False),
                             check_cmd=self.check)
        r = runner.run("conserte add", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["attempts"], 1)
        self.assertEqual(r["retries"], 0)

    def test_retry_com_feedback_recupera(self) -> None:
        ex = FakeExecutor(bug_antes=True)
        runner = AgentRunner(ex, check_cmd=self.check, max_attempts=2)
        r = runner.run("conserte add", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["attempts"], 2)
        self.assertEqual(r["retries"], 1)
        self.assertIn("não passou na verificação", ex.feedbacks[0])
        self.assertIn("Saída da verificação", ex.feedbacks[0])

    def test_falha_final_quando_check_nunca_passa(self) -> None:
        class Ruim(FakeExecutor):
            def _write(self, project_dir: str, com_bug: bool) -> dict[str, Any]:
                return self._write_sempre_ruim(project_dir)

            def _write_sempre_ruim(self, project_dir: str) -> dict[str, Any]:
                path = os.path.join(project_dir, "calc.py")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("def add(a, b):\n    return a - b\n")
                return {"files_written": ["calc.py"]}

        runner = AgentRunner(Ruim(), check_cmd=self.check, max_attempts=2)
        r = runner.run("conserte add", self.dir)
        self.assertFalse(r["finished"])
        self.assertEqual(r["attempts"], 2)
        self.assertEqual(r["retries"], 1)

    def test_projeto_inexistente_falha_sem_lancar(self) -> None:
        runner = AgentRunner(FakeExecutor(), check_cmd=self.check)
        r = runner.run("x", os.path.join(self.dir, "não_existe"))
        self.assertFalse(r["finished"])
        self.assertIn("não existe", r["error"])

    def test_sem_check_cmd_passa_direto(self) -> None:
        runner = AgentRunner(FakeExecutor(bug_antes=True))
        r = runner.run("x", self.dir)
        self.assertTrue(r["finished"])

    def test_store_registra_execucao(self) -> None:
        class FakeStore:
            def __init__(self) -> None:
                self.states: list[dict[str, Any]] = []
                self.task_id = "t1"
                self.db_name = "testdb"

                class _State:
                    last_backend = "fake"
                self.state = _State()

            def save_state(self, payload: dict[str, Any], task_id: str | None = None) -> dict[str, Any]:
                self.states.append(payload)
                return payload

        store = FakeStore()
        runner = AgentRunner(FakeExecutor(bug_antes=False),
                             check_cmd=self.check, store=store)
        runner.run("conserte add", self.dir)
        self.assertEqual(len(store.states), 1)
        e = store.states[0]
        self.assertEqual(e["status"], "completed")
        self.assertEqual(e["last_result"]["files"], ["calc.py"])

    def test_sem_store_nao_registra_nada(self) -> None:
        runner = AgentRunner(FakeExecutor(bug_antes=False),
                             check_cmd=self.check, store=None)
        r = runner.run("x", self.dir)  # não deve lançar
        self.assertTrue(r["finished"])

    def test_run_interno_do_modelo_passa(self) -> None:
        class ComRun(FakeExecutor):
            def execute(self, prompt: str, project_dir: str) -> dict[str, Any]:
                _ = prompt
                r = self._write(project_dir, False)
                r["run"] = "python -c \"print('validado')\""
                return r

        runner = AgentRunner(ComRun(), check_cmd=self.check)
        r = runner.run("x", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["internal_runs"], 1)

    def test_run_interno_falho_vira_feedback_e_retry(self) -> None:
        class RunRuim(FakeExecutor):
            def __init__(self) -> None:
                super().__init__(bug_antes=True)
                self.chamadas = 0

            def _respond(self, project_dir: str) -> dict[str, Any]:
                self.chamadas += 1
                com_bug = self.chamadas == 1
                r = self._write(project_dir, com_bug)
                r["run"] = "python -c \"import calc; assert calc.add(2, 3) == 5\""
                return r

            def execute(self, prompt: str, project_dir: str) -> dict[str, Any]:
                _ = prompt
                return self._respond(project_dir)

            def execute_with_feedback(
                self,
                prompt: str,
                project_dir: str,
                feedback: str,
            ) -> dict[str, Any]:
                _ = prompt
                self.feedbacks.append(feedback)
                return self._respond(project_dir)

        ex = RunRuim()
        runner = AgentRunner(ex, check_cmd=self.check, max_attempts=2)
        r = runner.run("conserte add", self.dir)
        self.assertTrue(r["finished"])
        self.assertEqual(r["internal_runs"], 2)
        self.assertIn("que você pediu para executar", ex.feedbacks[0])

    def test_run_interno_invalido_nao_lanca(self) -> None:
        class RunLouco(FakeExecutor):
            def execute(self, prompt: str, project_dir: str) -> dict[str, Any]:
                _ = prompt
                r = self._write(project_dir, False)
                r["run"] = "comando_que_nao_existe_12345"
                return r

        runner = AgentRunner(RunLouco(), check_cmd=[], max_attempts=1)
        r = runner.run("x", self.dir)
        self.assertFalse(r["finished"])
        self.assertIn("que você pediu para executar", r["error"])


class TestCheckRunner(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="check_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_cmd_ok(self) -> None:
        ok, out = CheckRunner().run(
            [sys.executable, "-c", "print('oi')"], self.dir)
        self.assertTrue(ok)
        self.assertIn("oi", out)

    def test_cmd_com_erro(self) -> None:
        ok, out = CheckRunner().run([sys.executable, "-c", "exit(3)"], self.dir)
        self.assertFalse(ok)
        self.assertIn("exit", out.lower())

    def test_cmd_inexistente_nao_lanca(self) -> None:
        ok, out = CheckRunner(timeout=5).run(
            ["definitivamente_nao_existe_cmd"], self.dir)
        self.assertFalse(ok)
        self.assertIn("erro ao executar check", out)


if __name__ == "__main__":
    unittest.main()
