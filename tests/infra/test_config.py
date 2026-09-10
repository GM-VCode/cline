# ============================================================
#  tests/test_config.py — testes unitários das helpers de Config
#  Usa SÓ a stdlib (unittest). Não toca .env real: exercita
#  os helpers de leitura/conversão isoladamente.
# ============================================================
# pyright: reportPrivateUsage=false

import os
import shutil
import tempfile
import unittest

from project_path import Config


class TestResolveModel(unittest.TestCase):
    """Auto-detecção do .gguf (MODEL_PATH vazio = detecta na pasta)."""

    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp(prefix="models_")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)

    def _write(self, name: str) -> str:
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as f:
            f.write("x")
        return path

    def test_usa_model_path_do_env_se_preenchido(self):
        env: dict[str, str] = {"MODEL_PATH": r"C:\models\meu.gguf"}
        self.assertEqual(Config._resolve_model(env), r"C:\models\meu.gguf")

    def test_detecta_unico_gguf_quando_env_vazio(self):
        from project_path import ProjectPath
        env: dict[str, str] = {}
        orig = ProjectPath.MODELS_DIR
        ProjectPath.MODELS_DIR = self.dir
        try:
            self._write("modelo.gguf")
            result = Config._resolve_model(env)
            self.assertTrue(result.endswith("modelo.gguf"), result)
            self.assertEqual(result, os.path.join(self.dir, "modelo.gguf"))
        finally:
            ProjectPath.MODELS_DIR = orig

    def test_vazio_quando_nao_ha_gguf(self):
        from project_path import ProjectPath
        orig = ProjectPath.MODELS_DIR
        ProjectPath.MODELS_DIR = self.dir
        try:
            self.assertEqual(Config._resolve_model({}), "")
        finally:
            ProjectPath.MODELS_DIR = orig

    def test_vazio_quando_ha_mais_de_um_gguf(self):
        from project_path import ProjectPath
        orig = ProjectPath.MODELS_DIR
        ProjectPath.MODELS_DIR = self.dir
        try:
            self._write("a.gguf")
            self._write("b.gguf")
            self.assertEqual(Config._resolve_model({}), "")
        finally:
            ProjectPath.MODELS_DIR = orig


class TestLoadDotenv(unittest.TestCase):
    def test_lee_claves_y_valores(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("ALIAS = LunarIA\nPORT=8080\nCTX=256512\n")
            path = f.name
        try:
            env = Config._load_dotenv(path)
        finally:
            os.unlink(path)
        self.assertEqual(env["ALIAS"], "LunarIA")
        self.assertEqual(env["PORT"], "8080")
        self.assertEqual(env["CTX"], "256512")

    def test_ignora_comentarios_y_vacios(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write("# comentario\n\nALIAS=x\n")
            path = f.name
        try:
            env = Config._load_dotenv(path)
        finally:
            os.unlink(path)
        self.assertNotIn("# comentario", env)
        self.assertEqual(env, {"ALIAS": "x"})

    def test_strips_comillas(self):
        with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
            f.write('HOST="127.0.0.1"\n')
            path = f.name
        try:
            env = Config._load_dotenv(path)
        finally:
            os.unlink(path)
        self.assertEqual(env["HOST"], "127.0.0.1")


class TestCastHelpers(unittest.TestCase):
    def test_as_int_default(self):
        self.assertEqual(Config._as_int({}, "PORT", 8080), 8080)
        self.assertEqual(Config._as_int({"PORT": "abc"}, "PORT", 7), 7)
        self.assertEqual(Config._as_int({"PORT": "4200"}, "PORT", 8080), 4200)

    def test_as_bool(self):
        # clave ausente => default
        self.assertTrue(Config._as_bool({}, "KILL", True))
        self.assertFalse(Config._as_bool({}, "KILL", False))
        # valores de activación
        self.assertTrue(Config._as_bool({"KILL": "1"}, "KILL", False))
        self.assertTrue(Config._as_bool({"KILL": "true"}, "KILL", False))
        self.assertTrue(Config._as_bool({"KILL": "yes"}, "KILL", False))
        self.assertTrue(Config._as_bool({"KILL": "on"}, "KILL", False))
        # valores de desactivación
        self.assertFalse(Config._as_bool({"KILL": "no"}, "KILL", True))
        self.assertFalse(Config._as_bool({"KILL": "0"}, "KILL", True))

    def test_as_opt(self):
        # vacío o 'none' => None (no se envía la flag)
        self.assertIsNone(Config._as_opt({}, "TEMP", float, 0.7))
        self.assertIsNone(Config._as_opt({"TEMP": "none"}, "TEMP", float, 0.7))
        self.assertEqual(Config._as_opt({"TEMP": "0.6"}, "TEMP", float, 0.7), 0.6)
        # cast inválido => default
        self.assertEqual(Config._as_opt({"TEMP": "oops"}, "TEMP", float, 0.7), 0.7)


class TestBaseUrl(unittest.TestCase):
    def test_base_url_se_deriva_de_host_y_port(self):
        cfg = Config()
        cfg.HOST = "127.0.0.1"
        cfg.PORT = 9000
        self.assertEqual(cfg.BASE_URL, "http://127.0.0.1:9000/v1")


if __name__ == "__main__":
    unittest.main()