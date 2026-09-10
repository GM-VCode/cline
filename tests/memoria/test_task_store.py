# ============================================================
#  tests/test_task_store.py — tests de TaskStore (modo fallback JSON)
#  Usa paths temporales y una URI que NO conecta (puerto cerrado),
#  así fija el modo JSON puro: no depende de MongoDB ni lo modifica.
# ============================================================

import os
import shutil
import tempfile
import unittest
from typing import TypedDict, Unpack, cast

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from data.mongodb.store import TaskStore  # noqa: E402


class TaskStoreOptions(TypedDict, total=False):
    uri: str
    db: str
    state_path: str
    validations_path: str
    timeout_ms: int
    model_name: str


class BaseTaskStoreTest(unittest.TestCase):
    URI_INVALIDA = "mongodb://127.0.0.1:1"  # puerto cerrado -> fallback JSON

    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="ts_test_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.state = os.path.join(self.dir, "state.json")
        self.vals = os.path.join(self.dir, "vals.json")

    def make(self, **kw: Unpack[TaskStoreOptions]) -> TaskStore:
        options: TaskStoreOptions = {
            "uri": self.URI_INVALIDA,
            "state_path": self.state,
            "validations_path": self.vals,
            "timeout_ms": 300,
        }
        options.update(kw)
        return TaskStore(**options)


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


class TestAgentRunsUpsert(BaseTaskStoreTest):
    """Upsert: 1 documento por conversa (task_id), sem duplicatas."""

    def test_upsert_atualiza_mesmo_doc_da_mesma_conversa(self):
        s = self.make()
        s.upsert_agent_run({"instruction": "missao X", "status": "in_progress",
                            "requests_count": 1, "run_id": "sid-1"},
                           task_id="sid-1")
        s.upsert_agent_run({"instruction": "missao X", "status": "in_progress",
                            "requests_count": 2, "run_id": "sid-1"},
                           task_id="sid-1")
        s.upsert_agent_run({"instruction": "missao X", "status": "in_progress",
                            "requests_count": 3, "run_id": "sid-1"},
                           task_id="sid-1")
        runs = s.list_agent_runs(limit=10, task_id="sid-1")
        self.assertEqual(len(runs), 1, "não pode acumular duplicatas")
        self.assertEqual(runs[0]["requests_count"], 3)
        self.assertEqual(runs[0]["status"], "in_progress")
        self.assertEqual(runs[0]["instruction"], "missao X")
        s.close()

    def test_upsert_nao_mistura_conversas_diferentes(self):
        s = self.make()
        s.upsert_agent_run({"instruction": "A", "requests_count": 1},
                           task_id="conv-a")
        s.upsert_agent_run({"instruction": "B", "requests_count": 1},
                           task_id="conv-b")
        s.upsert_agent_run({"instruction": "A", "requests_count": 2},
                           task_id="conv-a")
        runs_a = s.list_agent_runs(limit=10, task_id="conv-a")
        runs_b = s.list_agent_runs(limit=10, task_id="conv-b")
        self.assertEqual(len(runs_a), 1)
        self.assertEqual(len(runs_b), 1)
        self.assertEqual(runs_a[0]["requests_count"], 2)
        self.assertEqual(runs_b[0]["requests_count"], 1)
        self.assertEqual(runs_a[0]["instruction"], "A")
        self.assertEqual(runs_b[0]["instruction"], "B")
        s.close()

    def test_upsert_sobrescreve_campos_e_atualiza_ts(self):
        s = self.make()
        s.upsert_agent_run({"instruction": "v1", "status": "in_progress",
                            "error": ""}, task_id="sid-9")
        s.upsert_agent_run({"instruction": "v1", "status": "completed",
                            "error": "resolvido"}, task_id="sid-9")
        runs = s.list_agent_runs(limit=10, task_id="sid-9")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "completed")
        self.assertEqual(runs[0]["error"], "resolvido")
        self.assertIn("last_update", runs[0])
        s.close()

    def test_upsert_doc_com_created_at_nao_falha_no_mongo(self):
        """Regressão: doc do runstate vem com 'created_at'; o $set não pode
        conflitar com o $setOnInsert (derrubava tudo p/ fallback JSON)."""
        s = self.make()
        s.upsert_agent_run({"instruction": "oi", "status": "in_progress",
                            "created_at": "2026-09-08T20:00:00",
                            "last_seen_at": 1788904000.0},
                           task_id="sid-created")
        s.upsert_agent_run({"instruction": "oi", "status": "completed",
                            "created_at": "2026-09-08T20:00:00",
                            "last_seen_at": 1788904100.0},
                           task_id="sid-created")
        runs = s.list_agent_runs(limit=10, task_id="sid-created")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["status"], "completed")
        self.assertEqual(runs[0]["created_at"], "2026-09-08T20:00:00")
        s.close()

    def test_upsert_event_acumula_timeline(self):
        s = self.make()
        tid = "sid-timeline"
        s.upsert_agent_run({"instruction": "missao", "status": "in_progress"},
                           task_id=tid,
                           event={"tipo": "user_request", "ts": "t1",
                                  "nota": "pediu"})
        s.upsert_agent_run({"instruction": "missao", "status": "in_progress"},
                           task_id=tid,
                           event={"tipo": "model_tool", "ts": "t2",
                                  "nota": "ferramenta"})
        s.upsert_agent_run({"instruction": "missao", "status": "turn_finished"},
                           task_id=tid,
                           event={"tipo": "model_final", "ts": "t3",
                                  "nota": "respondeu"})
        runs = s.list_agent_runs(limit=10, task_id=tid)
        self.assertEqual(len(runs), 1, "não pode duplicar com timeline")
        timeline_value = runs[0].get("timeline")
        timeline: list[dict[str, object]] = cast(
            list[dict[str, object]],
            timeline_value if timeline_value is not None else [],
        )
        self.assertEqual([event["tipo"] for event in timeline],
                         ["user_request", "model_tool", "model_final"])
        self.assertEqual(timeline[-1]["nota"], "respondeu")
        s.close()

    def test_upsert_primeiro_event_cria_timeline(self):
        s = self.make()
        tid = "sid-novo"
        s.upsert_agent_run({"instruction": "missao", "status": "in_progress"},
                           task_id=tid,
                           event={"tipo": "user_request", "ts": "t0",
                                  "nota": "primeiro"})
        runs = s.list_agent_runs(limit=10, task_id=tid)
        self.assertEqual(len(runs), 1)
        self.assertEqual((runs[0].get("timeline") or [])[0]["tipo"],
                         "user_request")
        s.close()

    def test_get_agent_run_retorna_doc_ou_none(self):
        s = self.make()
        self.assertIsNone(s.get_agent_run("nao-existe"))
        s.upsert_agent_run({"instruction": "x", "status": "in_progress"},
                           task_id="sid-get")
        doc = s.get_agent_run("sid-get")
        self.assertIsNotNone(doc)
        assert doc is not None  # p/ o type checker
        self.assertEqual(doc["task_id"], "sid-get")
        self.assertEqual(doc["instruction"], "x")
        s.close()


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


class TestBenchmarkPorModelo(BaseTaskStoreTest):
    """benchmark_runs ÚNICA: 1 doc por modelo, corridas no timeline."""

    def test_append_benchmark_grava_nome_do_modelo(self):
        s = self.make(model_name="Q8_0")
        s.append_benchmark({"finish_rate": 0.9})
        s.close()
        s2 = self.make(model_name="Q8_0")
        runs = s2.list_benchmarks(limit=5)
        self.assertEqual(len(runs), 1, "1 doc por modelo")
        self.assertEqual(runs[0]["model"], "Q8_0")
        timeline: list[dict[str, object]] = runs[0].get("timeline") or []
        self.assertEqual(len(timeline), 1)
        self.assertEqual(timeline[0]["finish_rate"], 0.9)
        s2.close()

    def test_corridas_do_mesmo_modelo_acumulam_no_doc(self):
        s = self.make(model_name="Q8_0")
        s.append_benchmark({"finish_rate": 0.5})
        s.append_benchmark({"finish_rate": 0.9})
        s.close()
        s2 = self.make(model_name="Q8_0")
        runs = s2.list_benchmarks(limit=5)
        self.assertEqual(len(runs), 1, "não cria doc novo por corrida")
        self.assertEqual(len(runs[0].get("timeline") or []), 2)
        s2.close()

    def test_modelos_diferentes_ficam_em_docs_separados(self):
        a = self.make(model_name="Q8_0")
        a.append_benchmark({"finish_rate": 0.9})
        a.close()
        b = self.make(model_name="Q6_K")
        b.append_benchmark({"finish_rate": 0.5})
        b.close()
        a2 = self.make(model_name="Q8_0")
        b2 = self.make(model_name="Q6_K")
        runs_a = a2.list_benchmarks(limit=10)
        runs_b = b2.list_benchmarks(limit=10)
        self.assertEqual(len(runs_a), 1)
        self.assertEqual(runs_a[0]["model"], "Q8_0")
        self.assertEqual(len(runs_b), 1)
        self.assertEqual(runs_b[0]["model"], "Q6_K")
        a2.close()
        b2.close()


if __name__ == "__main__":
    unittest.main()