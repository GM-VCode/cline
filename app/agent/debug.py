# ============================================================
#  app/agent/debug.py — logger dedicado do agente
#  Escreve em logs/agent.log com nível DEBUG sempre (independe
#  do LOG_LEVEL do .env): prompt, resposta bruta do modelo,
#  arquivos aplicados e feedback de retry.
# ============================================================

import os

from project_path import Config
from tools.logger import AppLogger


def get_agent_logger() -> AppLogger:
    """AppLogger dedicado (logs/agent.log, nível DEBUG).

    Override de path via env AGENT_LOG_PATH (usado pelos tests
    para não poluírem o log real).
    """
    path = os.environ.get("AGENT_LOG_PATH") or Config().AGENT_LOG
    return AppLogger(name="agent", path=path, level="DEBUG")


def get_benchmark_logger() -> AppLogger:
    """AppLogger dedicado (logs/model/benchmark.log, nível DEBUG).

    Registra o ciclo do BenchmarkRunner: TASK → BEGIN → RESULT.
    Override de path via env BENCHMARK_LOG_PATH (tests).
    """
    path = os.environ.get("BENCHMARK_LOG_PATH") or Config().BENCHMARK_LOG
    return AppLogger(name="benchmark", path=path, level="DEBUG")


def get_executor_logger() -> AppLogger:
    """AppLogger dedicado (logs/model/executor.log, nível DEBUG).

    Registra REQUEST/RESPONSE bruto do LlamaExecutor.
    Override de path via env EXECUTOR_LOG_PATH (tests).
    """
    path = os.environ.get("EXECUTOR_LOG_PATH") or Config().EXECUTOR_LOG
    return AppLogger(name="executor", path=path, level="DEBUG")


def get_fallback_logger() -> AppLogger:
    """AppLogger dedicado (logs/app/fallback.log, nível DEBUG).

    Registra a ativação do fallback de memória (Mongo → JSON/temp).
    Override de path via env FALLBACK_LOG_PATH (tests).
    """
    path = os.environ.get("FALLBACK_LOG_PATH") or Config().FALLBACK_LOG
    return AppLogger(name="fallback", path=path, level="DEBUG")


def get_cline_use_logger() -> AppLogger:
    """AppLogger dedicado (logs/model/cline-use.log, nível DEBUG).

    Falhas e resumo do chat-bench do Cline (tools/cline_use).
    Override de path via env CLINE_USE_LOG_PATH (tests).
    """
    path = os.environ.get("CLINE_USE_LOG_PATH") or Config().CLINE_USE_LOG
    return AppLogger(name="cline-use", path=path, level="DEBUG")
