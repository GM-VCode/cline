# ============================================================
#  tests/test_recovery.py — tests de recuperação (resiliência)
#  Cenários adversos: JSON corrompido no disco, Mongo que cai
#  no meio de uma sessão, escrita em path inválido. O store
#  deve degradar com fallback (JSON/valor default) e NUNCA
#  propagar a falha ao chamador.
# ============================================================

import os
import shutil
import tempfile
import unittest
from typing import Any

from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()
ROOT = ProjectPath.ROOT

from data.mongodb.store import TaskStore          # noqa: E402
from data.mongodb.connection import MongoConnection  # noqa: E402
from data.mongodb.store.json_file import JsonFile   # noqa: E402
from data.mongodb.store.history import HistoryCollection  # noqa: E402
from data.mongodb.store.state import StateRepo       # noqa: E402


def corromper(path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("{isso não é json válido [[")


class FakeColl:
    """Coleção Mongo falsa que SEMPRE falha (simula queda)."""
    def insert_one(self, doc: dict[str, Any]) -> None:
        raise ConnectionError("mongo caiu")

    def replace_one(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs
        raise ConnectionError("mongo caiu")

    def find_one(self, *args: Any, **kwargs: Any) -> None:
        _ = args, kwargs
        raise ConnectionError("mongo caiu")


class FakeConn(MongoConnection):
    """Conexão 'ativa' cujas operações falham (Mongo caiu no meio)."""
    errors: list[str] = []

    def __init__(self) -> None:
        pass

    @property
    def active(self) -> bool:
        return True

    def collection(self, name: str) -> Any:
        _ = name
        return FakeColl()


class TestJsonCorrompido(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="recovery_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.state = os.path.join(self.dir, "state.json")
        self.vals = os.path.join(self.dir, "vals.json")

    def make(self) -> TaskStore:
        return TaskStore(uri="mongodb://127.0.0.1:1", state_path=self.state,
                         validations_path=self.vals, timeout_ms=300)

    def test_load_state_de_json_corrompido_vira_vazio(self):
        corromper(self.state)
        s = self.make()
        try:
            self.assertEqual(s.load_state(), {})
        finally:
            s.close()

    def test_save_state_recupera_depois_de_corrupcao(self):
        corromper(self.state)
        s = self.make()
        try:
            s.save_state({"objective": "novo"})
            self.assertEqual(s.load_state().get("objective"), "novo")
        finally:
            s.close()

    def test_list_validations_de_json_corrompido_vira_lista_vazia(self):
        corromper(self.vals)
        s = self.make()
        try:
            self.assertEqual(s.list_validations(), [])
        finally:
            s.close()

    def test_append_validation_recomeca_historico_corrompido(self):
        corromper(self.vals)
        s = self.make()
        try:
            entry = s.append_validation({"phase": "t", "result": "ok"})
            self.assertEqual(entry.get("phase"), "t")
            self.assertEqual(len(s.list_validations()), 1)
        finally:
            s.close()


class TestMongoCaiNoMeio(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="recovery_mongo_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.state = os.path.join(self.dir, "state.json")
        self.vals = os.path.join(self.dir, "vals.json")
        self.errors: list[str] = []
        self.conn = FakeConn()
        FakeConn.errors = self.errors

    def test_append_validation_cai_para_json_quando_mongo_falha(self):
        hist = HistoryCollection(self.conn, "validations", self.vals,
                                 "validations", error_sink=self.errors.append)
        entry = hist.append({"phase": "t"})
        self.assertEqual(entry.get("phase"), "t")          # não lançou
        self.assertEqual(len(hist.list(limit=10)), 1)      # caiu pro JSON
        self.assertTrue(any("validations" in m for m in self.errors))

    def test_save_state_cai_para_json_quando_mongo_falha(self):
        repo = StateRepo(self.conn, self.state, error_sink=self.errors.append)
        payload = repo.save({"objective": "x"})
        self.assertEqual(payload.get("objective"), "x")    # não lançou
        self.assertEqual(repo.load().get("objective"), "x")
        self.assertTrue(self.errors)

    def test_load_state_cai_para_json_quando_mongo_falha(self):
        JsonFile.write(self.state, {"objective": "do_json"})
        repo = StateRepo(self.conn, self.state, error_sink=self.errors.append)
        self.assertEqual(repo.load().get("objective"), "do_json")


class TestJsonFile(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="recovery_jf_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def test_read_corrompido_retorna_none(self):
        path = os.path.join(self.dir, "x.json")
        corromper(path)
        self.assertIsNone(JsonFile.read(path))

    def test_read_inexistente_retorna_none(self):
        self.assertIsNone(JsonFile.read(os.path.join(self.dir, "não_existe.json")))

    def test_write_em_path_invalido_retorna_false_sem_lancar(self):
        path = os.path.join(self.dir, "sub", "não_existe", "x.json")
        self.assertFalse(JsonFile.write(path, {"a": 1}))


if __name__ == "__main__":
    unittest.main()
