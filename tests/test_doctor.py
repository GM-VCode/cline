# ============================================================
#  tests/test_doctor.py — testes de ModelDoctor
#  Usa cfg fake (SimpleNamespace) e store com fallback JSON
#  (URI inválida): não depende do modelo real nem do Mongo.
# ============================================================

import os
import shutil
import tempfile
import unittest

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from project_path import Config  # noqa: E402
from tools.doctor import ModelDoctor  # noqa: E402
from data.mongodb.store import TaskStore  # noqa: E402


def fake_cfg(log_dir, model_ok=True):
    model = os.path.join(log_dir, "fake.gguf")
    if model_ok:
        with open(model, "w", encoding="utf-8") as f:
            f.write("x")
    server = os.path.join(log_dir, "llama-server.exe")
    if model_ok:
        with open(server, "w", encoding="utf-8") as f:
            f.write("x")
    cfg = Config()
    cfg.LLAMA_SERVER = server
    cfg.MODEL_PATH = model
    cfg.MM_PROJ_ENABLED = False
    cfg.MM_PROJ_PATH = ""
    cfg.CTX = 409600
    cfg.LOG_LEVEL = "INFO"
    cfg.LOG_DIR = log_dir
    cfg.APP_LOG = os.path.join(log_dir, "app.log")
    cfg.LOG_OUT = os.path.join(log_dir, "out.log")
    cfg.LOG_ERR = os.path.join(log_dir, "err.log")
    cfg.HOST = "127.0.0.1"
    cfg.PORT = 59999  # porta fechada -> warn
    return cfg


def fake_store(d):
    return TaskStore(
        uri="mongodb://127.0.0.1:1", timeout_ms=300,
        state_path=os.path.join(d, "state.json"),
        validations_path=os.path.join(d, "vals.json"))


class TestDoctor(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="doctor_test_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_saudavel_quando_paths_ok(self):
        d = doctor = None
        d = self.dir
        doctor = ModelDoctor(fake_cfg(d), fake_store(d))
        rc = doctor.run(save=False, verbose=False)
        self.assertEqual(rc, 0)
        statuses = {r["check"]: r["status"] for r in doctor.results}
        self.assertEqual(statuses["paths"], "ok")
        self.assertEqual(statuses["config"], "ok")
        self.assertEqual(statuses["logs"], "ok")
        self.assertEqual(statuses["mongo"], "warn")   # sem Mongo no teste
        self.assertEqual(statuses["servidor_api"], "warn")

    def test_falha_quando_modelo_ausente(self):
        doctor = ModelDoctor(fake_cfg(self.dir, model_ok=False),
                             fake_store(self.dir))
        rc = doctor.run(save=False, verbose=False)
        self.assertEqual(rc, 1)
        paths = next(r for r in doctor.results if r["check"] == "paths")
        self.assertEqual(paths["status"], "fail")
        self.assertIn("modelo ausente", paths["detail"])

    def test_diagnostic_salvo_no_fallback_json(self):
        store = fake_store(self.dir)
        doctor = ModelDoctor(fake_cfg(self.dir), store)
        doctor.run(save=True, verbose=False)
        diags = store.list_diagnostics(limit=5)
        self.assertEqual(len(diags), 1)
        self.assertIn("verdict", diags[0])
        self.assertTrue(os.path.isfile(
            os.path.join(self.dir, "diagnostics.json")))

    def test_debug_filtrado_por_level(self):
        from tools.logger import AppLogger
        log_path = os.path.join(self.dir, "level.log")
        log = AppLogger("t", path=log_path, level="INFO")
        log.debug("nao deve aparecer")
        log.info("deve aparecer")
        with open(log_path, encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("nao deve aparecer", content)
        self.assertIn("deve aparecer", content)


if __name__ == "__main__":
    unittest.main()