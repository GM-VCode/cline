# ============================================================
#  tools/benchmarks/tasks/ — pacote do catálogo do benchmark
#  (ex-tasks.py único, 241 linhas → modularizado)
#
#  Módulos:
#    core.py     → class BenchmarkTask
#    checks.py   → fábricas de check (arquivo/substring/unittest/expr)
#    catalog.py  → default_catalog() (11 tarefas, incl. 005X longa)
#
#  API pública preservada:
#    from tools.benchmarks.tasks import BenchmarkTask, default_catalog
# ============================================================

from tools.benchmarks.tasks.catalog import default_catalog  # noqa: F401
from tools.benchmarks.tasks.core import BenchmarkTask  # noqa: F401

__all__ = ["BenchmarkTask", "default_catalog"]
