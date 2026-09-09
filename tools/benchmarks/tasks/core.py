# ============================================================
#  tools/benchmarks/tasks/core.py — class BenchmarkTask
#  Uma tarefa padronizada do benchmark: id, categoria,
#  instrução, arquivos esperados e checks validáveis.
# ============================================================


class BenchmarkTask:
    """Uma tarefa padronizada do benchmark."""

    def __init__(self, task_id: str, category: str, instruction: str,
                 expected_files: list, checks: list):
        self.task_id = task_id
        self.category = category          # bug | feature | refactor | docs
        self.instruction = instruction    # prompt enviado ao modelo
        self.expected_files = expected_files
        self.checks = checks              # lista de (nome, callable)->(ok,msg)

    def run_checks(self, project_dir: str) -> list:
        """Executa os checks da tarefa; retorna [(check, ok, msg)]."""
        out = []
        for name, fn in self.checks:
            try:
                ok, msg = fn(project_dir)
            except Exception as exc:  # pragma: no cover
                ok, msg = False, f"exceção no check {name}: {exc}"
            out.append((name, ok, msg))
        return out
