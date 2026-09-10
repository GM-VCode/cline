# ============================================================
#  tools/cline_use/grader.py — Aplica a resposta do modelo e pontua
#  Avalia o USO das ferramentas: arquivos criados, sintaxe,
#  re-export no __init__, tipagem e o comando de verificação.
#  Cada check vira (nome, ok, detalhe) para o relatório final.
# ============================================================

import ast
import os
import subprocess
import sys


def full_content(path: str) -> str:
    """Lê o arquivo preservando comparação exata com o seed."""
    with open(path, encoding="utf-8") as f:
        return f.read()


class Grader:
    """Aplica a resposta do modelo num projeto e gera a pontuação."""

    def __init__(self, project_dir: str, timeout: int = 30) -> None:
        self.project_dir = project_dir
        self.timeout = timeout

    def grade(self, task, files: dict[str, str]) -> list[tuple[str, bool, str]]:
        """Executa todos os checks e retorna [(check, ok, detalhe)]."""
        results: list[tuple[str, bool, str]] = []
        results.append(self._check_escrita(files))
        results.append(self._check_sintaxe(files))
        results.append(self._check_imports(files, task.imports_ok))
        results.append(self._check_reexport(task.require_reexport))
        results.append(self._check_classe(task.require_class_file))
        results.append(self._check_tips(task.require_typed_init))
        results.append(self._check_untouched(task.require_untouched, task.seed_files))
        results.append(self._check_run(task.verify_cmd))
        return results

    # --- checks individuais -------------------------------------------

    def _check_escrita(self, files: dict[str, str]) -> tuple[str, bool, str]:
        if not files:
            return ("write_arquivos", False, "nenhum arquivo entregue no JSON")
        faltando = [p for p in files if not os.path.isfile(os.path.join(self.project_dir, p))]
        if faltando:
            return ("write_arquivos", False, f"não gravados: {faltando}")
        return ("write_arquivos", True, f"{len(files)} arquivo(s) gravados")

    def _check_sintaxe(self, files: dict[str, str]) -> tuple[str, bool, str]:
        erros: list[str] = []
        for path in files:
            full = os.path.join(self.project_dir, path)
            if not os.path.isfile(full):
                continue
            try:
                compile(open(full, encoding="utf-8").read(), path, "exec")
            except SyntaxError as exc:
                erros.append(f"{path}: {exc.msg} (linha {exc.lineno})")
        if erros:
            return ("sintaxe", False, "; ".join(erros))
        return ("sintaxe", True, "todos os arquivos compilam")

    def _check_imports(self, files: dict[str, str], mods: list[str]) -> tuple[str, bool, str]:
        if not mods:
            return ("imports", True, "n/a")
        for mod in mods:
            code = f"import {mod}"
            proc = subprocess.run([sys.executable, "-c", code],
                                  cwd=self.project_dir,
                                  capture_output=True, text=True, timeout=self.timeout)
            if proc.returncode != 0:
                motivo = (proc.stderr or "").strip().splitlines()
                return ("imports", False, f"{mod}: {motivo[-1] if motivo else 'erro'}")
        return ("imports", True, f"{len(mods)} módulo(s) importáveis")

    def _check_reexport(self, spec: tuple[str, str]) -> tuple[str, bool, str]:
        pacote, simbolo = spec
        if not pacote:
            return ("init_reexport", True, "n/a")
        code = f"from {pacote} import {simbolo}"
        proc = subprocess.run([sys.executable, "-c", code],
                              cwd=self.project_dir,
                              capture_output=True, text=True, timeout=self.timeout)
        if proc.returncode != 0:
            motivo = (proc.stderr or "").strip().splitlines()
            return ("init_reexport", False,
                    f"{pacote}.__init__ não exporta {simbolo}: "
                    f"{motivo[-1] if motivo else 'erro'}")
        return ("init_reexport", True, f"{pacote} exporta {simbolo}")

    def _check_classe(self, rel_path: str) -> tuple[str, bool, str]:
        if not rel_path:
            return ("classe_definida", True, "n/a")
        full = os.path.join(self.project_dir, rel_path)
        if not os.path.isfile(full):
            return ("classe_definida", False, f"{rel_path} ausente")
        tree = ast.parse(open(full, encoding="utf-8").read())
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        if not classes:
            return ("classe_definida", False, f"{rel_path} sem ClassDef")
        return ("classe_definida", True, f"classes: {classes}")

    def _check_tips(self, rel_path: str) -> tuple[str, bool, str]:
        if not rel_path:
            return ("tipagem_init", True, "n/a")
        full = os.path.join(self.project_dir, rel_path)
        if not os.path.isfile(full):
            return ("tipagem_init", False, f"{rel_path} ausente")
        tree = ast.parse(open(full, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for fn in node.body:
                    if isinstance(fn, ast.FunctionDef) and fn.name == "__init__":
                        args_sem_hint = [a.arg for a in fn.args.args
                                         if a.arg != "self" and a.annotation is None]
                        if args_sem_hint:
                            return ("tipagem_init", False,
                                    f"__init__ sem type hints: {args_sem_hint}")
                        return ("tipagem_init", True, "__init__ tipado")
        return ("tipagem_init", False, "nenhum __init__ encontrado")

    def _check_untouched(self, protegidos: list[str],
                         seeds: dict[str, str]) -> tuple[str, bool, str]:
        """Reprova o atalho de 'consertar' alterando o teste."""
        if not protegidos:
            return ("teste_intacto", True, "n/a")
        mexidos: list[str] = []
        for path in protegidos:
            full = os.path.join(self.project_dir, path)
            if not os.path.isfile(full):
                mexidos.append(f"{path} (removido)")
            elif path in seeds and full_content(full) != seeds[path]:
                mexidos.append(path)
        if mexidos:
            return ("teste_intacto", False, f"arquivo(s) de teste alterado(s): {mexidos}")
        return ("teste_intacto", True, "teste(s) preservado(s)")

    def _check_run(self, cmd: str) -> tuple[str, bool, str]:
        proc = subprocess.run(cmd, cwd=self.project_dir, shell=True,
                              capture_output=True, text=True, timeout=self.timeout)
        saida = ((proc.stdout or "") + (proc.stderr or "")).strip().splitlines()
        if proc.returncode != 0:
            return ("run_verificacao", False,
                    saida[-1] if saida else f"exit {proc.returncode}")
        return ("run_verificacao", True, saida[-1] if saida else "exit 0")
