# ============================================================
#  app/config.py — CONFIGURAÇÕES DO SERVIDOR (classe Config)
#  ★ NÃO edite este arquivo para valores que mudam de vez em
#  quando — use o arquivo  .env  na raiz do projeto.
#  Tudo (helpers de leitura + valores) vive DENTRO da classe.
#  Prioridade:  .env  >  defaults definidos na própria classe.
# ============================================================

import os


class Config:
    """Configuração efetiva do llama-server. Instancie: Config()."""

    # --------------------------------------------------------
    # HELPERS internos de leitura/conversão (usados no corpo
    # da própria classe para montar os atributos abaixo).
    # --------------------------------------------------------
    @staticmethod
    def _load_dotenv(path):
        env = {}
        if not os.path.isfile(path):
            return env
        try:
            with open(path, "r", encoding="utf-8") as f:
                for raw in f:
                    line = raw.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key:
                        env[key] = val
        except OSError:
            pass
        return env

    @staticmethod
    def _get(dotenv, key, default=""):
        raw = dotenv.get(key, "")
        return raw if raw != "" else str(default)

    @staticmethod
    def _as_int(dotenv, key, default):
        raw = dotenv.get(key, "")
        if raw == "":
            return default
        try:
            return int(float(raw))
        except ValueError:
            return default

    @staticmethod
    def _as_bool(dotenv, key, default):
        raw = dotenv.get(key, "").strip().lower()
        if raw == "":
            return default
        return raw in ("1", "true", "yes", "on")

    @staticmethod
    def _as_opt(dotenv, key, cast, default):
        """None se vazio/'none' (útil p/ sampling: não envia a flag)."""
        raw = dotenv.get(key, "").strip().lower()
        if raw in ("", "none"):
            return None
        try:
            return cast(raw)
        except ValueError:
            return default

    # --------------------------------------------------------
    # CAMINOS — BASE_DIR es la RAIZ del proyecto (padre de app\)
    # --------------------------------------------------------
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DOTENV = _load_dotenv(os.path.join(BASE_DIR, ".env"))

    # Logs centralizados DENTRO del proyecto (logs/)
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    LOG_OUT = os.path.join(LOG_DIR, "llama-server.out.log")
    LOG_ERR = os.path.join(LOG_DIR, "llama-server.err.log")
    APP_LOG = os.path.join(LOG_DIR, "app.log")

    # Binário del llama.cpp (global, fora del repo)
    LLAMA_SERVER = r"C:\llama.cpp\llama-server.exe"

    # --------------------------------------------------------
    # MODELO (default: models\ dentro do projeto)
    # --------------------------------------------------------
    ALIAS = _get(DOTENV, "ALIAS", "Qwythos-9B")
    MODEL_PATH = _get(
        DOTENV, "MODEL_PATH",
        os.path.join(BASE_DIR, "models", "Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-Q8_0.gguf"),
    )

    # --------------------------------------------------------
    # VISÃO (mmproj) — 1 = carrega | 0 = só texto
    # --------------------------------------------------------
    MM_PROJ_PATH = _get(
        DOTENV, "MM_PROJ_PATH",
        os.path.join(BASE_DIR, "visao", "Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-mmproj-BF16.gguf"),
    )
    MM_PROJ_ENABLED = _as_bool(DOTENV, "MM_PROJ_ENABLED", False)
    IMG_MIN_TOKENS = _as_int(DOTENV, "IMG_MIN_TOKENS", 1024)

    # --------------------------------------------------------
    # REDE
    # --------------------------------------------------------
    HOST = _get(DOTENV, "HOST", "127.0.0.1")
    PORT = _as_int(DOTENV, "PORT", 8080)

    # --------------------------------------------------------
    # HARDWARE / PERFORMANCE
    # --------------------------------------------------------
    NGL = _as_int(DOTENV, "NGL", 99)        # camadas na GPU (99 = tudo na VRAM)
    THREADS = _as_int(DOTENV, "THREADS", 12)
    CTX = _as_int(DOTENV, "CTX", 409600)    # contexto (múltiplo de 256)
    BATCH = _as_int(DOTENV, "BATCH", 1024)
    UBATCH = _as_int(DOTENV, "UBATCH", 512)

    # --------------------------------------------------------
    # SAMPLING (None = não envia a flag ao llama-server)
    # --------------------------------------------------------
    TEMP = _as_opt(DOTENV, "TEMP", float, 0.7)
    TOP_K = _as_opt(DOTENV, "TOP_K", int, 20)
    TOP_P = _as_opt(DOTENV, "TOP_P", float, 0.95)
    MIN_P = _as_opt(DOTENV, "MIN_P", float, 0.05)
    REPEAT_PENALTY = _as_opt(DOTENV, "REPEAT_PENALTY", float, 1.05)
    SEED = _as_opt(DOTENV, "SEED", int, -1)

    # --------------------------------------------------------
    # COMPORTAMENTO
    # --------------------------------------------------------
    KILL_OLD_INSTANCE = _as_bool(DOTENV, "KILL_OLD_INSTANCE", True)
    WAIT_HEALTH_SECONDS = _as_int(DOTENV, "WAIT_HEALTH_SECONDS", 120)
    LOG_LEVEL = _get(DOTENV, "LOG_LEVEL", "INFO")
    SHOW_CONFIG_ON_BOOT = _as_bool(DOTENV, "SHOW_CONFIG_ON_BOOT", True)

    # --------------------------------------------------------
    # Propriedades calculadas
    # --------------------------------------------------------
    @property
    def BASE_URL(self) -> str:
        """URL da API exposta ao Cline."""
        return f"http://{self.HOST}:{self.PORT}/v1"
