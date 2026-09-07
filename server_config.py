# ============================================================
#  server_config.py — CONFIGURAÇÕES DO SERVIDOR Qwythos-9B
#  ★ NÃO edites este arquivo para valores que cambian de vez
#  en quando — usa o fichero  .env  desta mesma pasta.
#  Este arquivo define os DEFAULTS e lee o .env em caso de
#  existir (as variables do .env têm prioridade).
# ============================================================

import os

# ------------------------------------------------------------
# BASE — carpeta onde está este projeto
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ------------------------------------------------------------
# CARGA DO .env  (parser simples, sem dependências)
#   Cria un fichero .env na mesma pasta deste server_config.py.
#   Formato por linha:  NOME = valor
#   - Não uses comillas obrigatoriamente (se já lee el texto tal cual)
#   - # comienza un comentario
# ------------------------------------------------------------
def _load_dotenv(path: str) -> dict:
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
    except Exception:
        pass
    return env

_DOTENV = _load_dotenv(os.path.join(BASE_DIR, ".env"))


def _s(val) -> str:
    """Valor string do .env ou default."""
    return _DOTENV.get(val, _DEFAULTS.get(val, ""))


def _i(val, default: int) -> int:
    raw = _DOTENV.get(val, "")
    if raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _f(val, default: float):
    raw = _DOTENV.get(val, "")
    if raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


_DEFAULTS = {
    # ---- MODELO / VISION ----
    "ALIAS": "Qwythos-9B",
    "MODEL_PATH": os.path.join(BASE_DIR, "models", "Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-Q8_0.gguf"),
    # Ruta do módulo de visão (carpeta visao\)
    "MM_PROJ_PATH": os.path.join(BASE_DIR, "visao", "Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic-mmproj-BF16.gguf"),
    # 1 = cargar visão | 0 = desactivarla (não se passa -mm)
    "MM_PROJ_ENABLED": "0",
    # Mínimo de tokens por imagem (Qwen-VL recomenda 1024 para precisão; só usado com visão)
    "IMG_MIN_TOKENS": "1024",
    # ---- REDE ----
    "HOST": "127.0.0.1",
    "PORT": "8080",
    # ---- HARDWARE ----
    "NGL": "99",
    "THREADS": "12",
    "CTX": "409600",
    "BATCH": "2048",
    "UBATCH": "512",
    # ---- SAMPLING ----
    "TEMP": "0.7",
    "TOP_K": "40",
    "TOP_P": "0.95",
    "MIN_P": "0.05",
    "REPEAT_PENALTY": "1.1",
    "SEED": "-1",
    # ---- COMPORTAMENTO ----
    "KILL_OLD_INSTANCE": "1",
    "WAIT_HEALTH_SECONDS": "120",
    "SHOW_CONFIG_ON_BOOT": "1",
}


# ============================================================
#  VALORES EFECTIVOS (usa o .env quando existir)
# ============================================================

# MODELO
ALIAS = _s("ALIAS")
MODEL_PATH = _s("MODEL_PATH")

# VISION
IMG_MIN_TOKENS = _i("IMG_MIN_TOKENS", 1024)
MM_PROJ_PATH = _s("MM_PROJ_PATH")
MM_PROJ_ENABLED = _s("MM_PROJ_ENABLED").lower() in ("1", "true", "yes", "on")

# REDE
HOST = _s("HOST")
PORT = _i("PORT", 8080)

# HARDWARE / PERFORMANCE
NGL = _i("NGL", 99)
THREADS = _i("THREADS", 12)
CTX = _i("CTX", 409600)
BATCH = _i("BATCH", 2048)
UBATCH = _i("UBATCH", 512)

# SAMPLING  (None = no enviar la flag)
_raw = _s("TEMP");       TEMP = None if _raw.lower() in ("none", "") else _f("TEMP", 0.7)
_raw = _s("TOP_K");      TOP_K = None if _raw.lower() in ("none", "") else _i("TOP_K", 40)
_raw = _s("TOP_P");      TOP_P = None if _raw.lower() in ("none", "") else _f("TOP_P", 0.95)
_raw = _s("MIN_P");      MIN_P = None if _raw.lower() in ("none", "") else _f("MIN_P", 0.05)
_raw = _s("REPEAT_PENALTY"); REPEAT_PENALTY = None if _raw.lower() in ("none", "") else _f("REPEAT_PENALTY", 1.1)
_raw = _s("SEED");       SEED = None if _raw.lower() in ("none", "") else _i("SEED", -1)

# CAMINHOS FIXOS
LLAMA_SERVER = r"C:\llama.cpp\llama-server.exe"
LOG_OUT = r"C:\llama.cpp\server.log"
LOG_ERR = r"C:\llama.cpp\server.err.log"

# COMPORTAMENTO
KILL_OLD_INSTANCE = _s("KILL_OLD_INSTANCE").lower() in ("1", "true", "yes", "on")
WAIT_HEALTH_SECONDS = _i("WAIT_HEALTH_SECONDS", 120)
SHOW_CONFIG_ON_BOOT = _s("SHOW_CONFIG_ON_BOOT").lower() in ("1", "true", "yes", "on")
