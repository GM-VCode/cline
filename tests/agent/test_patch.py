import os
import shutil
import sys
import tempfile
import unittest
from typing import Any

from app.agent.apply import PatchApplier
from app.agent.runner import AgentRunner


class EditorExecutor:
    def execute(
        self,
        instruction: str,
        /,
        project_dir: str,
    ) -> dict[str, Any]:
        with open(
            os.path.join(project_dir, "calc.py"),
            "w",
            encoding="utf-8",
        ) as file:
            file.write("def add(a, b):\n    return a + b\n")

        return {
            "tool_calls": 1,
            "retries": 0,
            "tokens": 0,
            "files_written": ["calc.py"],
            "files": {},
            "edits_applied": ["editado: calc.py"],
            "run": None,
        }

    def execute_with_feedback(
        self,
        instruction: str,
        /,
        project_dir: str,
        feedback: str,
    ) -> dict[str, Any]:
        return self.execute(instruction, project_dir)

    def execute_action(
        self,
        prompt: str,
        project_dir: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        return {"action": "done", "note": "teste concluído"}


class RejectedEditExecutor:
    def __init__(self) -> None:
        self.feedbacks: list[str] = []

    def execute(
        self,
        instruction: str,
        /,
        project_dir: str,
    ) -> dict[str, Any]:
        return {
            "tool_calls": 0,
            "retries": 0,
            "tokens": 0,
            "files_written": [],
            "files": {},
            "edits_failed": True,
            "edit_errors": ["edit[0]: 'find' não encontrado"],
            "run": None,
        }

    def execute_with_feedback(
        self,
        instruction: str,
        /,
        project_dir: str,
        feedback: str,
    ) -> dict[str, Any]:
        self.feedbacks.append(feedback)
        return self.execute(instruction, project_dir)

    def execute_action(
        self,
        prompt: str,
        project_dir: str,
        history: list[dict[str, str]],
    ) -> dict[str, Any] | None:
        return {"action": "done", "note": "teste concluído"}


class TestPatchApplier(unittest.TestCase):
    def setUp(self) -> None:
        self.project_dir = tempfile.mkdtemp(prefix="patch_")
        self.addCleanup(
            shutil.rmtree,
            self.project_dir,
            ignore_errors=True,
        )

        with open(
            os.path.join(self.project_dir, "grande.py"),
            "w",
            encoding="utf-8",
        ) as file:
            file.write(
                "def a():\n"
                "    return 1\n\n\n"
                "def b():\n"
                "    return 2\n\n\n"
                "def c():\n"
                "    return 3\n"
            )

    def read_file(self, name: str = "grande.py") -> str:
        with open(
            os.path.join(self.project_dir, name),
            encoding="utf-8",
        ) as file:
            return file.read()

    def test_patch_aplicado_troca_so_o_trecho(self) -> None:
        ok, report = PatchApplier().apply(
            self.project_dir,
            [{
                "file": "grande.py",
                "find": "return 2",
                "replace": "return 20",
            }],
        )

        self.assertTrue(ok, report)
        self.assertIn("return 20", self.read_file())
        self.assertIn("return 1", self.read_file())
        self.assertIn("return 3", self.read_file())

    def test_find_ambiguo_rejeita_sem_escrever(self) -> None:
        before = self.read_file()

        ok, report = PatchApplier().apply(
            self.project_dir,
            [{
                "file": "grande.py",
                "find": "    return",
                "replace": "x",
            }],
        )

        self.assertFalse(ok)
        self.assertIn("ambíguo", report[0])
        self.assertEqual(before, self.read_file())

    def test_find_inexistente_rejeita_e_mostra_conteudo(self) -> None:
        ok, report = PatchApplier().apply(
            self.project_dir,
            [{
                "file": "grande.py",
                "find": "NAO_EXISTE_123",
                "replace": "x",
            }],
        )

        self.assertFalse(ok)
        self.assertIn("não encontrado", report[0])
        self.assertIn("def a()", report[0])

    def test_arquivo_inexistente_pedindo_files(self) -> None:
        ok, report = PatchApplier().apply(
            self.project_dir,
            [{
                "file": "novo.py",
                "find": "a",
                "replace": "b",
            }],
        )

        self.assertFalse(ok)
        self.assertIn("use 'files'", report[0])
        self.assertFalse(
            os.path.exists(
                os.path.join(self.project_dir, "novo.py")
            )
        )

    def test_caminho_fora_do_projeto_rejeitado(self) -> None:
        ok, report = PatchApplier().apply(
            self.project_dir,
            [{
                "file": "../fora.py",
                "find": "a",
                "replace": "b",
            }],
        )

        self.assertFalse(ok)
        self.assertIn("fora do projeto", report[0])

    def test_edit_nao_dict_ou_incompleto(self) -> None:
        ok, report = PatchApplier().apply(
            self.project_dir,
            ["x"],
        )
        self.assertFalse(ok)

        ok, report = PatchApplier().apply(
            self.project_dir,
            [{
                "file": "grande.py",
                "find": "return 1",
            }],
        )

        self.assertFalse(ok)
        self.assertIn("obrigatórios", report[0])


class TestAgentRunnerEdits(unittest.TestCase):
    def setUp(self) -> None:
        self.project_dir = tempfile.mkdtemp(prefix="agent_patch_")
        self.addCleanup(
            shutil.rmtree,
            self.project_dir,
            ignore_errors=True,
        )

        with open(
            os.path.join(self.project_dir, "calc.py"),
            "w",
            encoding="utf-8",
        ) as file:
            file.write("def add(a, b):\n    return a - b\n")

        self.check = [
            sys.executable,
            "-c",
            "import calc; assert calc.add(2, 3) == 5",
        ]

    def test_edits_bons_aplicados_e_verificados(self) -> None:
        result = AgentRunner(
            EditorExecutor(),
            check_cmd=self.check,
        ).run("corrija a função add", self.project_dir)

        self.assertTrue(result["finished"])

        with open(
            os.path.join(self.project_dir, "calc.py"),
            encoding="utf-8",
        ) as file:
            self.assertIn("a + b", file.read())

    def test_edits_ruins_viram_feedback(self) -> None:
        result = AgentRunner(
            RejectedEditExecutor(),
            check_cmd=self.check,
            max_attempts=1,
        ).run("corrija a função add", self.project_dir)

        self.assertFalse(result["finished"])

        error = result.get("error")
        self.assertIsInstance(error, str)

        if isinstance(error, str):
            self.assertIn("REJEITADAS", error)


if __name__ == "__main__":
    unittest.main()
