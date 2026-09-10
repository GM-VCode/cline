# ============================================================
#  tests/test_proxy_sessions.py — tests do proxy de memória
#  URI inválida + paths temporários → fallback JSON puro:
#  não depende nem modifica o MongoDB real.
# ============================================================

import os
import shutil
import tempfile
import unittest
from typing import Any, TypedDict, Unpack

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from app.services.proxy.sessions import SessionRegistry  # noqa: E402
from app.task_store import TaskStore  # noqa: E402


class TaskStoreOptions(TypedDict, total=False):
    uri: str | None
    db: str | None
    state_path: str | None
    validations_path: str | None
    timeout_ms: int


class BaseProxyTest(unittest.TestCase):
    URI_INVALIDA = "mongodb://127.0.0.1:1"  # porta fechada -> fallback JSON

    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="proxy_test_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.state = os.path.join(self.dir, "state.json")
        self.vals = os.path.join(self.dir, "vals.json")

    def make_store(self, **kw: Unpack[TaskStoreOptions]) -> TaskStore:
        kw.setdefault("uri", self.URI_INVALIDA)
        kw.setdefault("state_path", self.state)
        kw.setdefault("validations_path", self.vals)
        kw.setdefault("timeout_ms", 300)
        return TaskStore(**kw)


class TestSessionRegistry(unittest.TestCase):
    def test_sid_da_primeira_mensagem_user(self):
        body: dict[str, Any] = {
            "messages": [{"role": "user",
                          "content": "Conserte o bug em calc.py"}],
        }
        sid = SessionRegistry.session_id(body)
        self.assertTrue(sid.startswith("u-"))

    def test_sid_estavel_para_mesma_conversa(self):
        body: dict[str, Any] = {
            "messages": [{"role": "system", "content": "sys"},
                         {"role": "user", "content": "missao X"}],
        }
        self.assertEqual(SessionRegistry.session_id(body),
                         SessionRegistry.session_id(body))

    def test_sid_explicito_tem_prioridade(self):
        body: dict[str, Any] = {
            "session_id": "abc-123",
            "messages": [{"role": "user", "content": "oi"}],
        }
        self.assertEqual(SessionRegistry.session_id(body), "abc-123")

    def test_fallback_default_sem_user(self):
        self.assertEqual(
            SessionRegistry.session_id({"messages": []}), "default")

    def test_multimodal_extrai_texto(self):
        body: dict[str, Any] = {
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "parte A"},
                {"type": "image_url", "image_url": {"url": "x"}},
            ]}],
        }
        self.assertEqual(SessionRegistry.session_id(body),
                         SessionRegistry.session_id({
                             "messages": [{"role": "user",
                                           "content": "parte A"}]}))

    def test_touch_conta_e_devolve_snapshot(self):
        r = SessionRegistry()
        body: dict[str, Any] = {
            "messages": [{"role": "user", "content": "missao Z"}],
        }
        s1 = r.touch(body)
        s2 = r.touch(body)
        self.assertEqual(s1["count"], 1)
        self.assertEqual(s2["count"], 2)
        self.assertEqual(s1["sid"], s2["sid"])


class TestPersistencia(BaseProxyTest):
    def test_save_e_load_com_task_id_da_sessao(self):
        s = self.make_store()
        s.save_state({"objective": "missao X"}, task_id="sessao-1")
        state = s.load_state(task_id="sessao-1")
        self.assertEqual(state.get("task_id"), "sessao-1")
        self.assertEqual(state.get("objective"), "missao X")
        self.assertEqual(s.load_state(task_id="sessao-2"), {})
        s.close()

    def test_agent_runs_filtram_por_task_id(self):
        s = self.make_store()
        s.append_agent_run({"instruction": "missao Y", "finished": False},
                           task_id="sessao-1")
        runs = s.list_agent_runs(limit=5, task_id="sessao-1")
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0]["instruction"], "missao Y")
        self.assertEqual(s.list_agent_runs(limit=5, task_id="sessao-2"), [])
        s.close()


if __name__ == "__main__":
    unittest.main()
