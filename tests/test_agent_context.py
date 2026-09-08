# ============================================================
#  tests/test_agent_context.py — tests da Etapa 9: ProjectContext
#  e AgentIdentity (visão do projeto no prompt, sem modelo).
# ============================================================

import os
import shutil
import sys
import tempfile
import unittest

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from app.agent import AgentIdentity, AgentRunner, ProjectContext  # noqa: E402


class FakeExecutor:
    """Grava a instrução recebida p/ inspecionar a composição."""

    def __init__(self):
        self.seen = []

    def execute(self, instruction, project_dir):
        self.seen.append(instruction)
        return {"files_written": [], "tokens": 1}

    def execute_with_feedback(self, instruction, project_dir, feedback):
        self.seen.append(instruction)
        return {"files_written": [], "tokens": 1}


class TestProjectContext(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ctx_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write(self, rel, content):
        path = os.path.join(self.dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_arvore_e_conteudo_no_prompt(self):
        self._write("src/app.py", "print('oi')")
        ctx = ProjectContext(self.dir)
        p = ctx.to_prompt()
        self.assertIn("src/app.py", p)
        self.assertIn("print('oi')", p)

    def test_diretorio_vazio(self):
        self.assertIn("vazio", ProjectContext(self.dir).to_prompt())

    def test_binario_ignorado_no_detalhe(self):
        self._write("img.png", "fake-bytes")
        p = ProjectContext(self.dir).to_prompt()
        self.assertNotIn("img.png", p)

    def test_skip_dirs(self):
        self._write("node_modules/pkg/index.js", "x=1")
        self._write(".venv/lib.py", "x=1")
        self._write("__pycache__/a.pyc", "x=1")
        self.assertEqual(ProjectContext(self.dir).tree, [])

    def test_limite_de_tamanho_trunca_detalhe(self):
        self._write("grande.py", "x = 1\n" * 5000)  # > 8 KB
        ctx = ProjectContext(self.dir)
        p = ctx.to_prompt()
        self.assertIn("grande.py", p)              # aparece na árvore
        self.assertNotIn("x = 1\n" * 100, p)       # conteúdo não entra

    def test_substituicao_de_backslash(self):
        self._write("sub/a.py", "ok")
        ctx = ProjectContext(self.dir)
        self.assertFalse(any("\\" in t for t in ctx.tree))


class TestAgentIdentity(unittest.TestCase):
    def test_carrega_identity_md_do_pacote(self):
        ident = AgentIdentity()
        self.assertIn("agente de código local", ident.to_prompt())
        self.assertIn("BLOQUEADO", ident.to_prompt())

    def test_arquivo_ausente_nao_lanca(self):
        ident = AgentIdentity(path=os.path.join(tempfile.gettempdir(),
                                                "não_existe.md"))
        self.assertEqual(ident.to_prompt(), "")


class TestRunnerComposicao(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="cmp_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        with open(os.path.join(self.dir, "calc.py"), "w",
                  encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

    def test_prompt_com_contexto_e_identidade(self):
        ex = FakeExecutor()
        AgentRunner(ex, identity=AgentIdentity()).run("conserte", self.dir)
        prompt = ex.seen[0]
        self.assertIn("INSTRUÇÃO: conserte", prompt)
        self.assertIn("calc.py", prompt)          # contexto
        self.assertIn("Quem você é", prompt)      # identidade

    def test_sem_contexto(self):
        ex = FakeExecutor()
        AgentRunner(ex, use_context=False).run("conserte", self.dir)
        self.assertNotIn("CONTEXTO DO PROJETO", ex.seen[0])

    def test_sem_identidade_por_padrao(self):
        ex = FakeExecutor()
        AgentRunner(ex).run("conserte", self.dir)
        self.assertNotIn("Quem você é", ex.seen[0])


if __name__ == "__main__":
    unittest.main()
