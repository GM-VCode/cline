# ============================================================
#  tests/test_server.py — testes de LlamaServer.build_args/validate
#  Usa SÓ la stdlib y un *stub* de config (SimpleNamespace), así
#  que NUNCA toca archivos reales, modelo, red ni VRAM.
# ============================================================

import os
import shutil
import sys
import tempfile
import types
import unittest

import app.services.server as server_mod
from app.services.server import LlamaServer

ROOT = server_mod.ROOT  # raíz del proyecto


def make_config(**overrides):
    """Config falsa con defaults conservadores para build_args/validate."""
    defaults = dict(
        LLAMA_SERVER=r"C:\llama.cpp\llama-server.exe",
        MODEL_PATH=r"C:\models\fake.gguf",
        MM_PROJ_ENABLED=False,
        MM_PROJ_PATH=r"C:\models\fake-mmproj.gguf",
        IMG_MIN_TOKENS=1024,
        ALIAS="LunarIA",
        HOST="127.0.0.1",
        PORT=8080,
        NGL=99,
        CTX=409600,
        THREADS=12,
        BATCH=1024,
        UBATCH=512,
        TEMP=None,       # None => no se envía la flag
        TOP_K=None,
        TOP_P=None,
        MIN_P=None,
        REPEAT_PENALTY=None,
        SEED=None,
    )
    defaults.update(overrides)
    return types.SimpleNamespace(**defaults)


def write_file(path, content="x"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


class TestBuildArgs(unittest.TestCase):
    def test_args_base_y_posiciones_clave(self):
        cfg = make_config(ALIAS="LunarIA", PORT=8080, NGL=25, CTX=131072)
        args = LlamaServer(cfg).build_args()
        self.assertIn(cfg.MODEL_PATH, args)
        self.assertIn("--alias", args)
        self.assertIn("LunarIA", args)
        self.assertIn("--port", args)
        self.assertIn("8080", args)
        self.assertIn("-ngl", args)
        self.assertIn("25", args)
        self.assertIn("-c", args)
        self.assertIn("131072", args)

    def test_flags_sampling_solo_con_valor(self):
        args = LlamaServer(make_config()).build_args()  # todos None
        for flag in ("--temp", "--top-k", "--top-p", "--min-p",
                     "--repeat-penalty", "--seed"):
            self.assertNotIn(flag, args)

    def test_flags_sampling_cuando_hay_valor(self):
        cfg = make_config(TEMP=0.6, TOP_K=20, TOP_P=0.95)
        args = LlamaServer(cfg).build_args()
        self.assertIn("--temp", args)
        self.assertIn("0.6", args)
        self.assertIn("--top-k", args)
        self.assertIn("--top-p", args)

    def test_vision_cuando_mmproj_activo(self):
        cfg = make_config(MM_PROJ_ENABLED=True)
        args = LlamaServer(cfg).build_args()
        self.assertIn("-mm", args)
        self.assertIn(cfg.MM_PROJ_PATH, args)
        self.assertIn("--image-min-tokens", args)

    def test_vision_desactivada_no_agrega_flag(self):
        cfg = make_config(MM_PROJ_ENABLED=False)
        args = LlamaServer(cfg).build_args()
        self.assertNotIn("-mm", args)
        self.assertNotIn("--image-min-tokens", args)


class TestValidate(unittest.TestCase):
    def _config_con_archivos_reales(self, **overrides):
        """Crea archivos temporales que persisten DURANTE el test y devuelve
        una config que apunta a ellos. Se limpian en el teardown."""
        d = tempfile.mkdtemp(prefix="cline_test_")
        self.addCleanup(shutil.rmtree, d, ignore_errors=True)
        llama = os.path.join(d, "llama-server.exe")
        model = os.path.join(d, "model.gguf")
        write_file(llama)
        write_file(model)
        return make_config(
            LLAMA_SERVER=llama,
            MODEL_PATH=model,
            **overrides,
        )

    def test_validacion_ok_no_levanta(self):
        cfg = self._config_con_archivos_reales(CTX=409600)
        # No debe imprimir errores ni llamar a sys.exit
        LlamaServer(cfg).validate()

    def test_archivos_faltantes_termina_con_error(self):
        cfg = make_config()  # paths apuntan a archivos inexistentes
        with self.assertRaises(SystemExit) as ctx:
            LlamaServer(cfg).validate()
        self.assertEqual(ctx.exception.code, 1)

    def test_ctx_no_multiplo_acumula_error(self):
        cfg = self._config_con_archivos_reales(CTX=1000)
        with self.assertRaises(SystemExit) as ctx:
            LlamaServer(cfg).validate()
        self.assertEqual(ctx.exception.code, 1)

    def test_mmproj_activo_pero_archivo_faltante_falla(self):
        cfg = self._config_con_archivos_reales(
            MM_PROJ_ENABLED=True,
            MM_PROJ_PATH=r"C:\models\nonexistent-mmproj.gguf",
        )
        with self.assertRaises(SystemExit) as ctx:
            LlamaServer(cfg).validate()
        self.assertEqual(ctx.exception.code, 1)

    def test_mmproj_activo_y_presente_ok(self):
        cfg = self._config_con_archivos_reales(MM_PROJ_ENABLED=True)
        mm = os.path.join(os.path.dirname(cfg.MODEL_PATH), "mmproj.gguf")
        write_file(mm)
        cfg.MM_PROJ_PATH = mm
        LlamaServer(cfg).validate()  # no levanta


if __name__ == "__main__":
    unittest.main()