# ============================================================
#  project_path/dotenv.py — helpers de leitura do .env
#  Funciones puras de carga/conversion (sin estado).
#  Extraido de project_path/ (regla de oro: >200 linhas -> pasta).
# ============================================================

import os
from typing import Callable, TypeVar

from project_path.paths import ProjectPath

_T = TypeVar("_T")


_LOG_FILES = {
    "DEBUG": "debug.log",
    "INFO": "info.log",
    "WARN": "warn.log",
    "ERROR": "error.log",
    "CRITICAL": "critical.log",
}
_ULTIMAS_LOGADAS: set[str] = set()


def _log(level: str, msg: str) -> None:
    """Loga em logs/app/<nível>.log SEM instanciar Config().

    Config() lê o .env via este próprio módulo: instanciar AppLogger com
    path padrão aqui causaria recursão infinita (bug já visto). Path e
    arquivo são construídos direto de ProjectPath. Import lazy porque
    tools.logger importa project_path (ciclo se fosse no topo). Guard de
    dedupe evita flood da mesma mensagem.
    """
    chave = f"{level}:{msg}"
    if chave in _ULTIMAS_LOGADAS:
        return
    _ULTIMAS_LOGADAS.add(chave)
    try:
        from tools.logger import AppLogger
        from tools.logger.levels import LogLevel
        arquivo = _LOG_FILES.get(LogLevel.normalize(level), "info.log")
        pasta = os.path.join(ProjectPath.LOG_DIR, "app")
        path = os.path.join(pasta, arquivo)
        AppLogger("config", path=path, level="DEBUG").log(level, msg)
    except Exception:  # pragma: no cover — logging nunca quebra a config
        pass


def load_dotenv(path: str) -> dict[str, str]:
    """Le o .env da raiz (chave=valor, ignora comentarios/vacios)."""
    env: dict[str, str] = {}
    if not os.path.isfile(path):
        _log("WARN", f".env não encontrado em {path} — usando defaults")
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
    except OSError as exc:
        _log("ERROR", f".env em {path} não pôde ser lido ({exc}) "
                      f"— usando defaults; configuração inválida em produção!")
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
    if len(gguFs) == 1:
        return os.path.join(models_dir, gguFs[0])
    if len(gguFs) > 1:
        _log("ERROR", f"MODEL_PATH vazio e {len(gguFs)} .gguf em "
                      f"{models_dir} — ambiguo, informe MODEL_PATH no .env")
    else:
        _log("ERROR", f"MODEL_PATH vazio e nenhum .gguf em {models_dir} "
                      f"— servidor não vai subir")
    return ""


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
    if len(gguFs) == 1:
        return os.path.join(models_dir, gguFs[0])
    if len(gguFs) > 1:
        _log("WARN", f"MM_PROJ_PATH={raw!r} ambiguo: {len(gguFs)} "
                     f"candidatos em {models_dir} — mmproj não carregado")
    else:
        _log("WARN", f"MM_PROJ_PATH={raw!r}: nenhum .gguf correspondente "
                     f"em {models_dir}")
    return raw


def as_int(dotenv: dict[str, str], key: str, default: int) -> int:
    """Converte a chave a int com default seguro (valor invalido loga WARN)."""
    raw = dotenv.get(key, "")
    if raw == "":
        return default
    try:
        return int(float(raw))
    except ValueError:
        _log("WARN", f"{key}={raw!r} não é int — usando default {default}")
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
        _log("WARN", f"{key}={raw!r} valor invalido "
                     f"— usando default {default!r}")
        return default