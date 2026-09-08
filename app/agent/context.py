# ============================================================
#  app/agent/context.py — class ProjectContext
#  Coleta a árvore de arquivos do projeto (com limites) e o
#  conteúdo dos arquivos de texto, para dar visão do código ao
#  modelo antes de editar.
# ============================================================

import os

SKIP_DIRS = {".git", "node_modules", ".venv", "__pycache__",
             "dist", "build", ".idea", ".vscode"}
MAX_FILE_BYTES = 8 * 1024        # conteúdo por arquivo
MAX_TOTAL_BYTES = 48 * 1024      # orçamento total do contexto
MAX_FILES = 60                   # nº máximo de arquivos no detalhe
BIN_EXT = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".zip", ".gz",
           ".exe", ".dll", ".pyc", ".woff", ".woff2", ".ttf", ".mp4"}


class ProjectContext:
    """Snapshot textual do projeto para incluir no prompt."""

    def __init__(self, project_dir: str, max_files: int = MAX_FILES,
                 max_total: int = MAX_TOTAL_BYTES) -> None:
        self.project_dir = project_dir
        self.max_files = max_files
        self.max_total = max_total
        self.tree, self.details, self.total_bytes = self._collect()

    def _is_skip(self, root: str, name: str) -> bool:
        return name in SKIP_DIRS or name.startswith(".")

    def _walk_files(self):
        for root, dirs, files in os.walk(self.project_dir):
            dirs[:] = [d for d in dirs if not self._is_skip(root, d)]
            for name in sorted(files):
                if os.path.splitext(name)[1].lower() in BIN_EXT:
                    continue
                yield os.path.join(root, name)

    def _collect(self) -> tuple[list[str], list[str], int]:
        tree, details, budget = [], [], 0
        for path in self._walk_files():
            rel = os.path.relpath(path, self.project_dir).replace("\\", "/")
            tree.append(rel)
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if (len(details) < self.max_files
                    and budget + size <= self.max_total
                    and size <= MAX_FILE_BYTES):
                try:
                    with open(path, "r", encoding="utf-8",
                              errors="replace") as f:
                        body = f.read()
                    details.append(f"--- {rel} ---\n{body}")
                    budget += min(size, len(body.encode("utf-8")))
                except OSError:
                    continue
        return tree, details, budget

    def to_prompt(self) -> str:
        if not self.tree:
            return "CONTEXTO DO PROJETO: (diretório vazio)"
        lines = ["CONTEXTO DO PROJETO (arquivos existentes):"]
        lines += [f"  {p}" for p in self.tree]
        if self.details:
            lines.append("\nCONTEÚDO DOS ARQUIVOS:")
            lines += self.details
        if len(self.tree) > len(self.details):
            lines.append("(arquivos além do limite aparecem só na árvore)")
        return "\n".join(lines)
