# ============================================================
#  project_path/config.py — class Config
#  Configuracion efectiva del llama-server (defaults + .env da
#  raiz). Prioridade: .env > defaults da propria classe.
#  Extraido de project_path/ (regla de oro: >200 linhas -> pasta).
# ============================================================

import os
from typing import Callable, TypeVar

from project_path.dotenv import (  # noqa: F401
    as_bool,
    as_int,
    as_opt,
    get,
    load_dotenv,
    resolve_mmproj,
    resolve_model,
)
from project_path.paths import ProjectPath

_T = TypeVar("_T")


class Config:
    """Configuracion efectiva del llama-server. Instancie: Config()."""

    # --------------------------------------------------------
    # HELPERS de lectura/conversion (delegan a dotenv.py)
    # --------------------------------------------------------
    @staticmethod
    def _load_dotenv(path: str) -> dict[str, str]:
        return load_dotenv(path)

    @staticmethod
    def _get(dotenv: dict[str, str], key: str, default: str = "") -> str:
        return get(dotenv, key, default)

    @staticmethod
    def _resolve_model(dotenv: dict[str, str]) -> str:
        return resolve_model(dotenv)

    def _resolve_mmproj(self, dotenv: dict[str, str]) -> str:
        return resolve_mmproj(dotenv)

    @staticmethod
    def _as_int(dotenv: dict[str, str], key: str, default: int) -> int:
        return as_int(dotenv, key, default)

    @staticmethod
    def _as_bool(dotenv: dict[str, str], key: str, default: bool) -> bool:
        return as_bool(dotenv, key, default)

    @staticmethod
    def _as_opt(dotenv: dict[str, str], key: str,
                cast: Callable[[str], _T], default: _T) -> _T | None:
        return as_opt(dotenv, key, cast, default)

    # --------------------------------------------------------
    # __init__ — TODOS os atributos de configuracion vivem aqui.
    # --------------------------------------------------------
    def __init__(self) -> None:
        # CAMINHOS — derivados da raiz unica (ProjectPath)
        self.BASE_DIR: str = ProjectPath.ROOT
        dotenv: dict[str, str] = self._load_dotenv(
            os.path.join(self.BASE_DIR, ".env"))

        self.LOG_DIR: str = ProjectPath.LOG_DIR
        # Logs organizados em subpastas (não misturar tudo em logs/)
        #   logs/proxy_and_server → llama-server, proxy, stack e status
        #   logs/model            → logs geradas nos testes de bench
        #   logs/app              → app.log + agent.log (runtime)
        self.LOG_OUT: str = os.path.join(self.LOG_DIR, "proxy_and_server",
                                         "llama-server.out.log")
        self.LOG_ERR: str = os.path.join(self.LOG_DIR, "proxy_and_server",
                                         "llama-server.err.log")
        self.APP_LOG: str = os.path.join(self.LOG_DIR, "app", "app.log")
        self.AGENT_LOG: str = os.path.join(self.LOG_DIR, "app", "agent.log")
        # logs/model → benchmark (TASK/BEGIN/RESULT) e executor
        # (REQUEST/RESPONSE bruto do LlamaExecutor)
        self.BENCHMARK_LOG: str = os.path.join(self.LOG_DIR, "model",
                                               "benchmark.log")
        self.EXECUTOR_LOG: str = os.path.join(self.LOG_DIR, "model",
                                              "executor.log")
        # fallback de memória (Mongo indisponível → JSON/temp): loga
        # SEMPRE que o fallback for ativado, para auditoria.
        self.FALLBACK_LOG: str = os.path.join(self.LOG_DIR, "app",
                                              "fallback.log")
        # chat-bench do Cline (tools/cline_use): falhas e resumo da
        # corrida, separado do Tee por-corrida (<MODELO>_<ts>.log).
        self.CLINE_USE_LOG: str = os.path.join(self.LOG_DIR, "model",
                                               "cline-use.log")

        # Binario do llama.cpp (global, fora do repo)
        self.LLAMA_SERVER: str = r"C:\llama.cpp\llama-server.exe"

        # MODELO (default: models\ dentro do projeto)
        self.ALIAS: str = self._get(dotenv, "ALIAS", "Qwythos-9B")
        self.MODEL_PATH: str = self._resolve_model(dotenv)

        # VISION (mmproj) — 1 = carrega | 0 = so texto
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
        # FLASH ATTENTION (on|off|auto): reduz a VRAM do KV
        self.FLASH_ATTN: str = self._get(dotenv, "FLASH_ATTN",
                                         "on").lower()
        # PARALLEL: n. de slots do servidor (1 = todo o CTX)
        self.PARALLEL: int = self._as_int(dotenv, "PARALLEL", 1)
        # KV_CACHE_TYPE: quantizacao do cache KV (q8_0 = ~metade VRAM)
        # KV_CACHE_TYPE: quantizacao do cache KV (q8_0 = ~metade VRAM)
        self.KV_CACHE_TYPE: str = self._get(dotenv, "KV_CACHE_TYPE",
                                            "q8_0").lower()

        # SAMPLING (None = nao envia a flag ao llama-server)
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

        # RACIOCINIO ( thinking): on | off | auto — "off" desliga o
        # thinking p/ todas as requisições (igual ao benchmark 9/10)
        self.REASONING: str = self._get(dotenv, "REASONING", "off").lower()
        # REASONING_PRESERVE: o template Qwen preserva reasoning por
        # DEFAULT no boot; com REASONING=off isso deixa o modelo
        # "pensar" (texto/plano) em vez de emitir tool calls.
        self.REASONING_PRESERVE: bool = self._as_bool(
            dotenv, "REASONING_PRESERVE", False)

    # --------------------------------------------------------
    # Propriedades calculadas
    # --------------------------------------------------------
    @property
    def BASE_URL(self) -> str:
        """URL da API exposta ao Cline."""
        return f"http://{self.HOST}:{self.PORT}/v1"