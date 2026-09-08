# ============================================================
#  tests/test_logger.py — separação de logs por nível (split)
# ============================================================

import os
import shutil
import tempfile
import unittest


class TestLoggerSplit(unittest.TestCase):
    """AppLogger com split por nível → um .log exclusivo por nível."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="logsplit_")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _read(self, name: str) -> str:
        path = os.path.join(self.dir, name)
        if not os.path.isfile(path):
            return ""
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_cada_nivel_em_seu_arquivo(self):
        from tools.logger import AppLogger
        log = AppLogger("t", path=os.path.join(self.dir, "app.log"),
                        level="DEBUG", split_levels=True)
        log.debug("msg-debug")
        log.info("msg-info")
        log.warn("msg-warn")
        log.error("msg-error")
        self.assertIn("msg-debug", self._read("debug.log"))
        self.assertIn("msg-info", self._read("info.log"))
        self.assertIn("msg-warn", self._read("warn.log"))
        self.assertIn("msg-error", self._read("error.log"))

    def test_arquivos_exclusivos_por_nivel(self):
        from tools.logger import AppLogger
        log = AppLogger("t", path=os.path.join(self.dir, "app.log"),
                        level="DEBUG", split_levels=True)
        log.info("so-info")
        log.error("so-erro")
        self.assertNotIn("so-info", self._read("debug.log"))
        self.assertNotIn("so-info", self._read("warn.log"))
        self.assertNotIn("so-info", self._read("error.log"))
        self.assertNotIn("so-erro", self._read("debug.log"))
        self.assertNotIn("so-erro", self._read("warn.log"))
        self.assertNotIn("so-erro", self._read("info.log"))
        self.assertIn("so-erro", self._read("error.log"))

    def test_path_custom_sem_split_mantem_arquivo_unico(self):
        from tools.logger import AppLogger
        unico = os.path.join(self.dir, "unico.log")
        log = AppLogger("t", path=unico, level="DEBUG")
        log.info("tudo-junto")
        log.error("tudo-junto")
        with open(unico, encoding="utf-8") as f:
            content = f.read()
        self.assertEqual(content.count("tudo-junto"), 2)
        self.assertFalse(os.path.isfile(os.path.join(self.dir, "info.log")))

    def test_level_minimo_respeitado_com_split(self):
        from tools.logger import AppLogger
        log = AppLogger("t", path=os.path.join(self.dir, "app.log"),
                        level="INFO", split_levels=True)
        log.debug("filtrado")
        log.warning("alias-warn")
        self.assertNotIn("filtrado", self._read("debug.log"))
        self.assertNotIn("filtrado", self._read("info.log"))
        self.assertIn("alias-warn", self._read("warn.log"))

    def test_traceback_vai_para_o_arquivo_do_nivel(self):
        from tools.logger import AppLogger
        log = AppLogger("t", path=os.path.join(self.dir, "app.log"),
                        level="DEBUG", split_levels=True)
        try:
            raise ValueError("boom-123")
        except ValueError:
            log.error("falhou", exc_info=True)
        self.assertIn("boom-123", self._read("error.log"))
        self.assertNotIn("boom-123", self._read("info.log"))


if __name__ == "__main__":
    unittest.main()
