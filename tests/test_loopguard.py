# ============================================================
#  tests/test_loopguard.py — LoopGuard do proxy
#  Contrato (TDD): detecta requests idênticas consecutivas por
#  sessão e decide a intervenção (aviso + temperature bump).
# ============================================================

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.proxy.loopguard import LoopGuard  # noqa: E402


def make_body(text: str) -> dict:
    return {"model": "LunarIA",
            "messages": [{"role": "user", "content": text}]}


class TestRequestHash(unittest.TestCase):
    def test_hash_estavel_para_o_mesmo_body(self):
        g = LoopGuard()
        h1 = g.request_hash(make_body("faca x"))
        h2 = g.request_hash(make_body("faca x"))
        self.assertEqual(h1, h2)

    def test_hash_diferente_para_conteudo_diferente(self):
        g = LoopGuard()
        self.assertNotEqual(g.request_hash(make_body("faca x")),
                            g.request_hash(make_body("faca y")))

    def test_hash_ignora_campo_temperature(self):
        """Só as mensagens importam: retry com temp diferente é o mesmo pedido."""
        g = LoopGuard()
        a = make_body("faca x")
        b = make_body("faca x")
        b["temperature"] = 0.9
        self.assertEqual(g.request_hash(a), g.request_hash(b))

    def test_hash_de_body_malformado_nao_levanta(self):
        g = LoopGuard()
        self.assertIsInstance(g.request_hash({}), str)
        self.assertIsInstance(g.request_hash({"messages": None}), str)


class TestVerdict(unittest.TestCase):
    def test_primeira_request_passa_sem_intervencao(self):
        g = LoopGuard()
        aviso, temp = g.register("s1", g.request_hash(make_body("oi")))
        self.assertIsNone(aviso)
        self.assertIsNone(temp)

    def test_segunda_identica_gera_nudge_e_temp_07(self):
        g = LoopGuard()
        h = g.request_hash(make_body("faca x"))
        g.register("s1", h)
        aviso, temp = g.register("s1", h)
        assert aviso is not None and temp is not None
        self.assertIn("menores", aviso.lower())
        self.assertAlmostEqual(temp, 0.7)

    def test_terceira_identica_gera_aviso_forte_e_temp_09(self):
        g = LoopGuard()
        h = g.request_hash(make_body("faca x"))
        g.register("s1", h)
        g.register("s1", h)
        aviso, temp = g.register("s1", h)
        assert aviso is not None and temp is not None
        self.assertAlmostEqual(temp, 0.9)

    def test_mudanca_de_conteudo_reseta_o_contador(self):
        g = LoopGuard()
        h1 = g.request_hash(make_body("faca x"))
        g.register("s1", h1)
        g.register("s1", h1)                      # 2x → nudge
        h2 = g.request_hash(make_body("agora faca y"))
        aviso, temp = g.register("s1", h2)        # conteúdo mudou → reset
        self.assertIsNone(aviso)
        self.assertIsNone(temp)
        aviso, temp = g.register("s1", h2)        # de novo idêntico → 2ª vez
        assert aviso is not None and temp is not None

    def test_sessoes_nao_se_misturam(self):
        g = LoopGuard()
        h = g.request_hash(make_body("faca x"))
        g.register("s1", h)
        aviso, _ = g.register("s2", h)            # sessão diferente → 1ª vez
        self.assertIsNone(aviso)

    def test_acima_do_limite_mantem_aviso_forte(self):
        g = LoopGuard()
        h = g.request_hash(make_body("faca x"))
        aviso, temp = None, None
        for _ in range(6):
            aviso, temp = g.register("s1", h)
        assert aviso is not None and temp is not None
        self.assertAlmostEqual(temp, 0.9)


if __name__ == "__main__":
    unittest.main()
