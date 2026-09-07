# ============================================================
#  tools/benchmarks/report.py — class BenchmarkReport
#  Resumo dos resultados do benchmark + persistência no
#  histórico (Mongo coleção benchmark_runs, fallback JSON).
# ============================================================

import sys
import time

# Força UTF-8 no stdout para evitar UnicodeEncodeError (cp1252 no Windows CMD)
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class BenchmarkReport:
    """Resume resultados e persiste corridas do benchmark."""

    def __init__(self, store=None):
        self.store = store  # TaskStore (pode ser None)

    def summarize(self, results: list) -> dict:
        total = len(results)
        finished = sum(1 for r in results if r["finished"])
        return {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "total_tasks": total,
            "finished": finished,
            "finish_rate": round(finished / total, 2) if total else 0.0,
            "avg_elapsed_s": (round(sum(r["elapsed_s"] for r in results) / total, 2)
                              if total else 0.0),
            "avg_tool_calls": (round(sum(r["tool_calls"] for r in results) / total, 2)
                               if total else 0.0),
            "avg_retries": (round(sum(r["retries"] for r in results) / total, 2)
                            if total else 0.0),
            "total_files_created": sum(r["files_created"] for r in results),
            "tasks": [
                {k: r[k] for k in ("task_id", "category", "finished",
                                   "checks_passed", "checks_total",
                                   "elapsed_s", "tool_calls", "retries",
                                   "files_created")}
                for r in results
            ],
        }

    def save(self, summary: dict) -> dict:
        if self.store is None:
            return summary
        try:
            self.store.append_benchmark(summary)
        except Exception:  # pragma: no cover
            pass
        return summary

    @staticmethod
    def print_summary(summary: dict):
        print("=" * 62)
        print("  BENCHMARK — resumo")
        print("=" * 62)
        print(f"  tarefas: {summary['finished']}/{summary['total_tasks']} "
              f"concluídas (taxa {summary['finish_rate']:.0%})")
        print(f"  tempo médio: {summary['avg_elapsed_s']}s | "
              f"tool_calls médios: {summary['avg_tool_calls']} | "
              f"retries médios: {summary['avg_retries']}")
        print("-" * 62)
        for t in summary["tasks"]:
            icon = "[OK]" if t["finished"] else "[X]"
            print(f"  {icon} {t['task_id']:<26} "
                  f"{t['checks_passed']}/{t['checks_total']} checks "
                  f"{t['elapsed_s']}s")
        print("=" * 62)