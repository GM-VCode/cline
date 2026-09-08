# ============================================================
#  project_path.py — FONTE ÚNICA do projeto (caminhos + config)
#
#  1) ProjectPath — raiz, diretórios e sys.path centralizados.
#     O sis.pth (.venv/Lib/site-packages/sis.pth) adiciona o
#     cwd ao sys.path na inicialização; ProjectPath.ensure()
#     garante o mesmo de forma idempotente para qualquer CLI.
#  2) Config — configuração efetiva (defaults + leitura do .env
#     da raiz). Prioridade: .env > defaults da própria classe.
#
#  app/config.py apenas re-exporta Config (compatibilidade):
#      from project_path import Config   # padrão interno
#      from app.config import Config     # continua funcionando
# ============================================================

import os
import sys
from typing import Callable, TypeVar

_T = TypeVar("_T")


class ProjectPath:
    """Caminhos raiz + sys.path centralizados (fonte única)."""

    ROOT: str = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR: str = os.path.join(ROOT, "data", "json")
    LOG_DIR: str = os.path.join(ROOT, "logs")
    MODELS_DIR: str = os.path.join(ROOT, "models")

    @classmethod
    def ensure(cls) -> None:
        """Garante que a raiz esteja no sys.path (idempotente)."""
        if cls.ROOT not in sys.path:
            sys.path.insert(0, cls.ROOT)

    @classmethod
    def join(cls, *parts: str) -> str:
        """Caminho absoluto dentro do projeto (sem repetir dirname)."""
        return os.path.join(cls.ROOT, *parts)

    @classmethod
    def root(cls) -> str:
        return cls.ROOT


class Config:
    """Configuração efetiva do llama-server. Instancie: Config()."""

    # --------------------------------------------------------
    # HELPERS de leitura/conversão (estáticos; usados no __init__)
    # --------------------------------------------------------
    @staticmethod
    def _load_dotenv(path: str) -> dict[str, str]:
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

    @staticmethod
    def _get(dotenv: dict[str, str], key: str, default: str = "") -> str:
        raw = dotenv.get(key, "")
        return raw if raw != "" else str(default)

    @staticmethod
    def _resolve_model(dotenv: dict[str, str]) -> str:
        """Caminho do modelo.

        Se MODEL_PATH estiver preenchido no .env, usa direto.
        Se vazio, auto-detecta o ÚNICO .gguf da pasta models/:
          - 1 arquivo  -> usa ele
          - 0 ou >1    -> retorna "" (validate() falha com mensagem clara)
        """
        raw = dotenv.get("MODEL_PATH", "").strip()
        if raw:
            return raw
        models_dir = ProjectPath.MODELS_DIR
        gguFs = sorted(
            f for f in os.listdir(models_dir)
            if f.lower().endswith(".gguf")) if os.path.isdir(models_dir) else []
        return os.path.join(models_dir, gguFs[0]) if len(gguFs) == 1 else ""

    def _resolve_mmproj(self, dotenv: dict[str, str]) -> str:
        """Caminho do mmproj (visual).

        - Se MM_PROJ_PATH vazio no .env -> "" (modo só texto)
        - Se for um caminho absoluto (contém \\ ou /) -> usa direto
        - Se for nome de arquivo (ex: Qwythos-...-Q8_0.gguf) -> resolve em models/
        - Se for ID base do modelo (ex: Qwythos-9B-Claude-Mythos-5-1M-uncensored-
          heretic) -> busca mmproj qualquer em models/ que contenha esse ID
        """
        raw = dotenv.get("MM_PROJ_PATH", "").strip()
        if not raw:
            return ""
        # caminho absoluto: usa como está
        if "\\" in raw or "/" in raw:
            return raw
        models_dir = ProjectPath.MODELS_DIR
        if not os.path.isdir(models_dir):
            return ""
        files = os.listdir(models_dir)
        gguFs = sorted(f for f in files
                       if f.lower() == raw.lower() and f.lower().endswith(".gguf"))
        if gguFs:
            return os.path.join(models_dir, gguFs[0])
        # não achou nome exato -> tenta como ID base do modelo
        # (ex: "Qwythos-9B-Claude-Mythos-5-1M-uncensored-heretic" ->
        #  qualquer .gguf em models/ que contenha esse ID)
        gguFs = sorted(f for f in files
                       if raw in f and f.lower().endswith(".gguf"))
        return os.path.join(models_dir, gguFs[0]) if len(gguFs) == 1 else raw

    @staticmethod
    def _as_int(dotenv: dict[str, str], key: str, default: int) -> int:
        raw = dotenv.get(key, "")
        if raw == "":
            return default
        try:
            return int(float(raw))
        except ValueError:
            return default

    @staticmethod
    def _as_bool(dotenv: dict[str, str], key: str, default: bool) -> bool:
        raw = dotenv.get(key, "").strip().lower()
        if raw == "":
            return default
        return raw in ("1", "true", "yes", "on")

    @staticmethod
    def _as_opt(dotenv: dict[str, str], key: str,
                cast: Callable[[str], _T], default: _T) -> _T | None:
        """None se vazio/'none' (útil p/ sampling: não envia a flag)."""
        raw = dotenv.get(key, "").strip().lower()
        if raw in ("", "none"):
            return None
        try:
            return cast(raw)
        except ValueError:
            return default

    # --------------------------------------------------------
    # __init__ — TODOS os atributos de configuração vivem aqui.
    # O .env da raiz é lido a cada instanciação (arquivo pequeno).
    # --------------------------------------------------------
    def __init__(self) -> None:
        # CAMINHOS — derivados da raiz única (ProjectPath)
        self.BASE_DIR: str = ProjectPath.ROOT
        dotenv: dict[str, str] = self._load_dotenv(
            os.path.join(self.BASE_DIR, ".env"))

        self.LOG_DIR: str = ProjectPath.LOG_DIR
        self.LOG_OUT: str = os.path.join(self.LOG_DIR,
                                         "llama-server.out.log")
        self.LOG_ERR: str = os.path.join(self.LOG_DIR,
                                         "llama-server.err.log")
        self.APP_LOG: str = os.path.join(self.LOG_DIR, "app.log")
        self.AGENT_LOG: str = os.path.join(self.LOG_DIR, "agent.log")

        # Binário do llama.cpp (global, fora do repo)
        self.LLAMA_SERVER: str = r"C:\llama.cpp\llama-server.exe"

        # MODELO (default: models\ dentro do projeto)
        self.ALIAS: str = self._get(dotenv, "ALIAS", "Qwythos-9B")
        # MODEL_PATH vazio = auto-detecta o .gguf da pasta models/
        # (troque o modelo apenas GARANTINDO que haja UM .gguf; sem erro)
        self.MODEL_PATH: str = self._resolve_model(dotenv)

        # VISÃO (mmproj) — 1 = carrega | 0 = só texto
        self.MM_PROJ_PATH: str = self._resolve_mmproj(dotenv)
        self.MM_PROJ_ENABLED: bool = self._as_bool(dotenv,
                                                   "MM_PROJ_ENABLED", False)
        self.IMG_MIN_TOKENS: int = self._as_int(dotenv, "IMG_MIN_TOKENS",
                                                1024)

        # REDE
        self.HOST: str = self._get(dotenv, "HOST", "127.0.0.1")
        self.PORT: int = self._as_int(dotenv, "PORT", 8080)

        # HARDWARE / PERFORMANCE
        self.NGL: int = self._as_int(dotenv, "NGL", 99)      # 99 = tudo GPU
        self.THREADS: int = self._as_int(dotenv, "THREADS", 12)
        self.CTX: int = self._as_int(dotenv, "CTX", 409600)  # mult. de 256
        self.BATCH: int = self._as_int(dotenv, "BATCH", 1024)
        self.UBATCH: int = self._as_int(dotenv, "UBATCH", 512)
        # FLASH ATTENTION (on|off|auto): reduz a VRAM do KV e acelera o
        # prompt processing — recomendado para 16 GB com CTX grande.
        self.FLASH_ATTN: str = self._get(dotenv, "FLASH_ATTN",
                                         "on").lower()
        # PARALLEL: nº de slots do servidor. Para uso solo no Cline, 1
        # slot concentra todo o CTX numa conversa (sem fragmentar).
        self.PARALLEL: int = self._as_int(dotenv, "PARALLEL", 1)
        # KV_CACHE_TYPE: quantização do cache KV (q8_0|f16...). Q8_0
        # ~metade da VRAM com perda mínima — ideal em 16 GB.
        self.KV_CACHE_TYPE: str = self._get(dotenv, "KV_CACHE_TYPE",
                                            "q8_0").lower()

        # SAMPLING (None = não envia a flag ao llama-server)
        self.TEMP: float | None = self._as_opt(dotenv, "TEMP", float, 0.7)
        self.TOP_K: int | None = self._as_opt(dotenv, "TOP_K", int, 20)
        self.TOP_P: float | None = self._as_opt(dotenv, "TOP_P",
                                                float, 0.95)
        self.MIN_P: float | None = self._as_opt(dotenv, "MIN_P",
                                                float, 0.05)
        self.REPEAT_PENALTY: float | None = self._as_opt(
            dotenv, "REPEAT_PENALTY", float, 1.05)
        self.SEED: int | None = self._as_opt(dotenv, "SEED", int, -1)

        # COMPORTAMENTO
        self.KILL_OLD_INSTANCE: bool = self._as_bool(dotenv,
                                                     "KILL_OLD_INSTANCE",
                                                     True)
        self.WAIT_HEALTH_SECONDS: int = self._as_int(
            dotenv, "WAIT_HEALTH_SECONDS", 120)
        self.LOG_LEVEL: str = self._get(dotenv, "LOG_LEVEL", "INFO")
        self.SHOW_CONFIG_ON_BOOT: bool = self._as_bool(
            dotenv, "SHOW_CONFIG_ON_BOOT", True)

        # RACIOCÍNIO (<think>): on | off | auto — "off" desliga o
        # thinking p/ todas as requisições (igual ao benchmark 9/10;
        # o default "auto" do llama.cpp degradava o tool calling no Cline)
        self.REASONING: str = self._get(dotenv, "REASONING", "off").lower()

    # --------------------------------------------------------
    # Propriedades calculadas
    # --------------------------------------------------------
    @property
    def BASE_URL(self) -> str:
        """URL da API exposta ao Cline."""
        return f"http://{self.HOST}:{self.PORT}/v1"
