# ============================================================
#  tools/benchmarks/tasks/core.py — class BenchmarkTask
#  Uma tarefa padronizada do benchmark: id, categoria,
#  instrução, arquivos esperados e checks validáveis.
# ============================================================

from collections.abc import Callable

CheckFn = Callable[[str], tuple[bool, str]]
CheckEntry = tuple[str, CheckFn]
CheckResult = tuple[str, bool, str]


class BenchmarkTask:
    """Uma tarefa padronizada do benchmark."""

    def __init__(
        self,
        task_id: str,
        category: str,
        instruction: str,
        expected_files: list[str],
        checks: list[CheckEntry],
    ) -> None:
        self.task_id = task_id
        self.category = category          # bug | feature | refactor | docs
        self.instruction = instruction    # prompt enviado ao modelo
        self.expected_files = expected_files
        self.checks = checks              # lista de (nome, callable)->(ok,msg)

    def run_checks(self, project_dir: str) -> list[CheckResult]:
        """Executa os checks da tarefa; retorna [(check, ok, msg)]."""
        out: list[CheckResult] = []
        for name, fn in self.checks:
            try:
                ok, msg = fn(project_dir)
            except Exception as exc:  # pragma: no cover
                ok, msg = False, f"exceção no check {name}: {exc}"
                from app.agent.debug import get_benchmark_logger
                blog = get_benchmark_logger()
                if blog:
                    blog.error(f"check {name!r} estourou exceção: {exc}")
            out.append((name, ok, msg))
        return out
