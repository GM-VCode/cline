# ============================================================
#  tests/test_runstate.py — máquina de estados + StreamProbe
#  Testa as funções puras do pacote app/services/proxy/runstate
#  (sem I/O): aplicação de request/resposta, promoção por
#  timeout e detecção de finish_reason/tool_calls no streaming.
# ============================================================

import unittest

from app.services.proxy import runstate


class TestBaseDoc(unittest.TestCase):
    def test_base_doc_inicial(self):
        doc = runstate.base_doc("sid-1", "crie algo", 1_700_000_000.0)
        self.assertEqual(doc["task_id"], "sid-1")
        self.assertEqual(doc["instruction"], "crie algo")
        self.assertEqual(doc["status"], runstate.IN_PROGRESS)
        self.assertFalse(doc["finished"])
        self.assertEqual(doc["requests_count"], 0)
        self.assertEqual(doc["timeline"], [])

    def test_instruction_truncada_a_500(self):
        doc = runstate.base_doc("s", "x" * 900, 1.0)
        self.assertEqual(len(doc["instruction"]), 500)


class TestApplyRequest(unittest.TestCase):
    def test_primeiro_request_vira_in_progress(self):
        doc = runstate.base_doc("s", "missao", 100.0)
        doc = runstate.apply_request(doc, "missao", 110.0)
        self.assertEqual(doc["status"], runstate.IN_PROGRESS)
        self.assertFalse(doc["finished"])
        self.assertEqual(doc["requests_count"], 1)
        self.assertEqual(doc["timeline"][-1]["tipo"], "user_request")

    def test_reabre_conversa_completed(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "stop", False, 2.0, check_ok=True)
        self.assertEqual(doc["status"], runstate.COMPLETED)
        doc = runstate.apply_request(doc, "pera, está errado", 3.0)
        self.assertEqual(doc["status"], runstate.IN_PROGRESS)
        self.assertFalse(doc["finished"])
        self.assertEqual(doc["timeline"][-1]["tipo"], "user_reopen")
        # o modelo pode reabrir com "falha de verificação"

    def test_loop_limit_marca_failed(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        n = runstate.MAX_REQUESTS_LOOP
        for i in range(n):
            doc = runstate.apply_request(doc, "mais um", float(i) + 2.0)
        self.assertEqual(doc["status"], runstate.FAILED)
        self.assertTrue(doc["finished"])
        self.assertEqual(doc["timeline"][-1]["tipo"], "loop_limit")


class TestApplyResponse(unittest.TestCase):
    def test_tool_calls_mantem_in_progress(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "", True, 2.0)
        self.assertEqual(doc["status"], runstate.IN_PROGRESS)
        self.assertFalse(doc["finished"])
        self.assertEqual(doc["last_finish_reason"], "")
        self.assertEqual(doc["timeline"][-1]["tipo"], "model_tool")

    def test_stop_sem_tool_vira_turn_finished(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "stop", False, 2.0)
        self.assertEqual(doc["status"], runstate.TURN_FINISHED)
        self.assertFalse(doc["finished"])  # honesto: não declarou pronto
        self.assertEqual(doc["last_finish_reason"], "stop")
        self.assertEqual(doc["timeline"][-1]["tipo"], "model_final")

    def test_check_ok_marca_completed_direto(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "stop", False, 2.0, check_ok=True)
        self.assertEqual(doc["status"], runstate.COMPLETED)
        self.assertTrue(doc["finished"])
        self.assertEqual(doc["timeline"][-1]["tipo"], "check_ok")

    def test_length_vira_turn_finished(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "length", False, 2.0)
        self.assertEqual(doc["status"], runstate.TURN_FINISHED)
        self.assertEqual(doc["timeline"][-1]["tipo"], "context_limit")


class TestPromoteTimeout(unittest.TestCase):
    def test_nao_promove_turno_recente(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "stop", False, 2.0)
        doc2 = runstate.promote_timeout(doc, 3.0, grace_s=300)
        self.assertEqual(doc2["status"], runstate.TURN_FINISHED)

    def test_promove_turno_antigo_sem_request(self):
        doc = runstate.base_doc("s", "missao", 1.0)
        doc = runstate.apply_response(doc, "stop", False, 2.0)
        # 30 min depois (sem novo request)
        doc2 = runstate.promote_timeout(doc, 2.0 + 1800, grace_s=300)
        self.assertEqual(doc2["status"], runstate.COMPLETED)
        self.assertTrue(doc2["finished"])
        self.assertEqual(doc2["timeline"][-1]["tipo"], "auto_complete")

    def test_so_promove_estado_turn_finished(self):
        doc = runstate.apply_request(runstate.base_doc("s", "m", 1.0), "m", 2.0)
        doc2 = runstate.promote_timeout(doc, 2.0 + 1800, grace_s=300)
        self.assertEqual(doc2["status"], runstate.IN_PROGRESS)


class TestStreamProbe(unittest.TestCase):
    def test_detecta_tool_calls_e_finish_reason(self):
        p = runstate.StreamProbe()
        chunk1 = b'data: {"choices":[{"delta":{"tool_calls":["x"]}}]}'
        chunk2 = b'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}'
        p.feed(chunk1)
        p.feed(chunk2)
        finish, has_tool = p.snapshot()
        self.assertTrue(has_tool)
        self.assertIn("tool_calls", finish)

    def test_detecta_stop(self):
        p = runstate.StreamProbe()
        p.feed(b'data: {"choices":[{"finish_reason":"stop"}]}')
        finish, has_tool = p.snapshot()
        self.assertEqual(finish, "stop")
        self.assertFalse(has_tool)

    def test_vazio_mantem_estado_neutro(self):
        p = runstate.StreamProbe()
        finish, has_tool = p.snapshot()
        self.assertEqual(finish, "")
        self.assertFalse(has_tool)


if __name__ == "__main__":
    unittest.main()