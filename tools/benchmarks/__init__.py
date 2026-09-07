# tools/benchmarks — benchmark do agente (roda separado do modelo)
#
#  tasks.py    -> class BenchmarkTask + catálogo padronizado
#  runner.py   -> class ModelExecutor (stub plugável) + BenchmarkRunner
#  report.py   -> class BenchmarkReport (resumo + histórico)
#
#  Uso (futuro, com modelo real):
#    python -m tools.benchmarks.runner