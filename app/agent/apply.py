# ============================================================
#  app/agent/apply.py — class PatchApplier
#  Aplica edições cirúrgicas ("edits") em arquivos existentes:
#  [{"file": ..., "find": ..., "replace": ...}]. Regra de
#  segurança: "find" deve ocorrer EXATAMENTE 1x no arquivo —
#  0x (não achou) ou 2x+ (ambíguo) rejeita a edição inteira
#  sem modificar nada. Escrita completa continua via "files".
# ============================================================

import os


class PatchApplier:
    """Aplica edições de trecho em arquivos de projeto, com atomicidade."""

    def apply(self, project_dir: str, edits) -> tuple:
        """Aplica uma lista de edits. Retorna (ok: bool, report: list[str]).

        Todas as edições são validadas ANTES de qualquer escrita: se uma
        falhar, nenhuma é aplicada (o projeto não fica pela metade).
        """
        if not isinstance(edits, list):
            return False, ["campo 'edits' deve ser uma lista"]
        project_dir = os.path.abspath(project_dir)
        # 1) valida tudo primeiro (lê os arquivos alvo)
        plans = []
        for i, edit in enumerate(edits):
            plan = self._validate_one(project_dir, edit, i)
            if isinstance(plan, str):  # mensagem de erro
                return False, [plan]
            plans.append(plan)
        # 2) aplica (sempre em arquivo validado, find único garantido)
        report = []
        for path, find, replace in plans:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(content.replace(find, replace, 1))
            report.append(f"editado: {os.path.relpath(path, project_dir)}")
        return True, report

    def _validate_one(self, project_dir: str, edit, index: int):
        """Valida um edit; retorna plano (path, find, replace) ou erro str."""
        if not isinstance(edit, dict):
            return f"edit[{index}]: deve ser objeto {{file, find, replace}}"
        rel = edit.get("file") or ""
        find = edit.get("find")
        replace = edit.get("replace")
        if not rel or find is None or replace is None:
            return f"edit[{index}]: campos obrigatórios file/find/replace"
        path = os.path.abspath(os.path.join(project_dir, rel))
        if not path.startswith(project_dir):
            return f"edit[{index}]: caminho fora do projeto ({rel!r})"
        if not os.path.isfile(path):
            return (f"edit[{index}]: arquivo não existe: {rel!r} "
                    f"(para criar, use 'files' em vez de 'edits')")
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except (OSError, UnicodeDecodeError) as exc:
            return f"edit[{index}]: não consegui ler {rel!r}: {exc}"
        count = content.count(find)
        if count == 0:
            return (f"edit[{index}]: 'find' não encontrado em {rel!r}. "
                    f"Início real do arquivo: {content[:200]!r}")
        if count > 1:
            return (f"edit[{index}]: 'find' ambíguo em {rel!r} "
                    f"({count} ocorrências) — inclua mais contexto")
        return path, find, replace
