# -*- coding: utf-8 -*-
"""Testes das fábricas de checks que executam código real.

Usa fallback/temp: nunca toca no MongoDB nem no modelo.
"""
import os
import shutil
import tempfile
import unittest

from tools.benchmarks.tasks.checks import python_expr_ok, unittest_ok

MOD = "def add(a, b):\n    return a + b\n"


class TestPythonExprOk(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="checks_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        with open(os.path.join(self.dir, "calc.py"), "w",
                  encoding="utf-8") as f:
            f.write("def add(a, b):\n    return a + b\n")

    def test_expr_verdadeira_passa_sem_nameerror(self):
        ok, msg = python_expr_ok("calc", "add(2, 3) == 5")(self.dir)
        self.assertTrue(ok, msg)

    def test_expr_falsa_falha_com_mensagem(self):
        ok, msg = python_expr_ok("calc", "add(2, 3) == 6")(self.dir)
        self.assertFalse(ok)
        self.assertIn("FALSO", msg)


class TestUnittestOk(unittest.TestCase):
    def test_teste_passando_e_ok(self):
        d = tempfile.mkdtemp(prefix="unittest_ok_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "test_ok.py"), "w",
                  encoding="utf-8") as f:
            f.write("import unittest\n\n\nclass T(unittest.TestCase):\n"
                    "    def test_ok(self):\n        self.assertTrue(True)\n")
        ok, msg = unittest_ok("test_ok.py")(d)
        self.assertTrue(ok, msg)

    def test_teste_falhando_e_falha(self):
        d = tempfile.mkdtemp(prefix="unittest_fail_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        with open(os.path.join(d, "test_bad.py"), "w",
                  encoding="utf-8") as f:
            f.write("import unittest\n\n\nclass T(unittest.TestCase):\n"
                    "    def test_bad(self):\n        self.assertTrue(False)\n")
        ok, _msg = unittest_ok("test_bad.py")(d)
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
