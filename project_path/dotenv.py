# ============================================================
#  project_path/dotenv.py — helpers de leitura do .env
#  Funciones puras de carga/conversion (sin estado).
#  Extraido de project_path/ (regla de oro: >200 linhas -> pasta).
# ============================================================

import os
from typing import Callable, TypeVar

from project_path.paths import ProjectPath

_T = TypeVar("_T")


def load_dotenv(path: str) -> dict[str, str]:
    """Le o .env da raiz (chave=valor, ignora comentarios/vacios)."""
    env: dict[str, str] = {}
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


def get(dotenv: dict[str, str], key: str, default: str = "") -> str:
    """Valor da chave com default (default si vazia)."""
    raw = dotenv.get(key, "")
    return raw if raw != "" else str(default)


def resolve_model(dotenv: dict[str, str]) -> str:
    """Caminho do modelo: MODEL_PATH preenchido ou auto-detecta models/."""
    raw = dotenv.get("MODEL_PATH", "").strip()
    if raw:
        return raw
    models_dir = ProjectPath.MODELS_DIR
    gguFs = sorted(
        f for f in os.listdir(models_dir)
        if f.lower().endswith(".gguf")) if os.path.isdir(models_dir) else []
    return os.path.join(models_dir, gguFs[0]) if len(gguFs) == 1 else ""


def resolve_mmproj(dotenv: dict[str, str]) -> str:
    """Caminho do mmproj (visual).

    - Vazio no .env -> "" (modo so texto)
    - Caminho absoluto (contiene \\\\ o /) -> usa direto
    - Nome de arquivo (ex: Qwythos-...-Q8_0.gguf) -> resolve em models/
    - ID base (ex: Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic) ->
      qualquer .gguf em models/ que contenha esse ID
    """
    raw = dotenv.get("MM_PROJ_PATH", "").strip()
    if not raw:
        return ""
    if "\\\\" in raw or "/" in raw:
        return raw
    models_dir = ProjectPath.MODELS_DIR
    if not os.path.isdir(models_dir):
        return ""
    files = os.listdir(models_dir)
    gguFs = sorted(f for f in files
                   if f.lower() == raw.lower() and f.lower().endswith(".gguf"))
    if gguFs:
        return os.path.join(models_dir, gguFs[0])
    gguFs = sorted(f for f in files
                   if raw in f and f.lower().endswith(".gguf"))
    return os.path.join(models_dir, gguFs[0]) if len(gguFs) == 1 else raw


def as_int(dotenv: dict[str, str], key: str, default: int) -> int:
    """Converte a chave a int com default seguro."""
    raw = dotenv.get(key, "")
    if raw == "":
        return default
    try:
        return int(float(raw))
    except ValueError:
        return default


def as_bool(dotenv: dict[str, str], key: str, default: bool) -> bool:
    """Converte a chave a bool (1/true/yes/on) com default seguro."""
    raw = dotenv.get(key, "").strip().lower()
    if raw == "":
        return default
    return raw in ("1", "true", "yes", "on")


def as_opt(dotenv: dict[str, str], key: str,
           cast: Callable[[str], _T], default: _T) -> _T | None:
    """None se vazio/'none' (util p/ sampling: non envia a flag)."""
    raw = dotenv.get(key, "").strip().lower()
    if raw in ("", "none"):
        return None
    try:
        return cast(raw)
    except ValueError:
        return default