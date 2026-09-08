# ============================================================
#  tests/test_task_store.py — tests de TaskStore (modo fallback JSON)
#  Usa paths temporales y una URI que NO conecta (puerto cerrado),
#  así fija el modo JSON puro: no depende de MongoDB ni lo modifica.
# ============================================================

import os
import shutil
import tempfile
import unittest

import sys
from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from app.task_store import TaskStore  # noqa: E402


class BaseTaskStoreTest(unittest.TestCase):
    URI_INVALIDA = "mongodb://127.0.0.1:1"  # puerto cerrado -> fallback JSON

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="ts_test_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.state = os.path.join(self.dir, "state.json")
        self.vals = os.path.join(self.dir, "vals.json")

    def make(self, **kw):
        kw.setdefault("uri", self.URI_INVALIDA)
        kw.setdefault("state_path", self.state)
        kw.setdefault("validations_path", self.vals)
        kw.setdefault("timeout_ms", 300)
        return TaskStore(**kw)


class TestFallbackJSON(BaseTaskStoreTest):
    def test_falla_a_json_y_no_es_mongo(self):
        s = self.make()
        self.assertFalse(s.active)
        # no debe haber error fatal: solo notar que usa JSON
        s.close()

    def test_save_y_load_roundtrip(self):
        s = self.make()
        s.save_state({"objective": "mi_objetivo", "next_action": "x"})
        s.close()
        s2 = self.make()
        state = s2.load_state()
        self.assertEqual(state.get("objective"), "mi_objetivo")
        self.assertEqual(state.get("task_id"), "current")
        self.assertIn("updated_at", state)
        s2.close()


class TestAgentRuns(BaseTaskStoreTest):
    def test_append_y_list_agent_runs(self):
        s = self.make()
        s.append_agent_run({"instruction": "conserte add", "finished": True,
                            "attempts": 1, "retries": 0,
                            "files": ["calc.py"], "elapsed_s": 1.5})
        s.append_agent_run({"instruction": "outra", "finished": False,
                            "attempts": 2, "retries": 1, "files": []})
        runs = s.list_agent_runs(limit=10)
        self.assertEqual(len(runs), 2)
        self.assertEqual(runs[0]["instruction"], "outra")  # mais recente 1.º
        self.assertIn("ts", runs[0])
        s.close()

    def test_agent_runs_fallback_json_arquivo(self):
        s = self.make()
        s.append_agent_run({"instruction": "x", "finished": True})
        s.close()
        path = os.path.join(os.path.dirname(self.vals), "agent_runs.json")
        self.assertTrue(os.path.isfile(path))


class TestValidations(BaseTaskStoreTest):
    def test_append_y_list(self):
        s = self.make()
        s.append_validation({"phase": "unittest", "result": "ok", "exit_code": 0})
        s.append_validation({"phase": "unittest", "result": "fail", "exit_code": 1})
        s.close()

        s2 = self.make()
        vals = s2.list_validations(limit=10)
        self.assertEqual(len(vals), 2)
        # el orden: los más recientes primero
        self.assertEqual(vals[0]["result"], "fail")
        self.assertEqual(vals[1]["result"], "ok")
        s2.close()

    def test_limite(self):
        s = self.make()
        for i in range(5):
            s.append_validation({"phase": "t", "result": "ok", "n": i})
        s.close()
        s2 = self.make()
        vals = s2.list_validations(limit=2)
        self.assertEqual(len(vals), 2)
        s2.close()


class TestFallbackSinMongo(BaseTaskStoreTest):
    def test_active_false_cuando_no_hay_mongo(self):
        s = self.make()
        self.assertFalse(s.active)


if __name__ == "__main__":
    unittest.main()