# ============================================================
#  tools/benchmarks/tasks/checks.py — fábricas de check
#  Cada fábrica devolve um callable (project_dir)->(ok, msg).
#  Checks simples (arquivo/substring) + checks que EXECUTAM
#  código de verdade (unittest real e expressão real).
# ============================================================

import os


def file_contains(rel_path: str, needle: str):
    """Fábrica de check: arquivo existe e contém `needle`."""
    def check(project_dir: str):
        path = os.path.join(project_dir, rel_path)
        if not os.path.isfile(path):
            return False, f"arquivo ausente: {rel_path}"
        with open(path, "r", encoding="utf-8") as f:
            if needle in f.read():
                return True, f"{rel_path} contém '{needle}'"
        return False, f"{rel_path} não contém '{needle}'"
    return check


def file_exists(rel_path: str):
    """Fábrica de check: arquivo existe."""
    def check(project_dir: str):
        exists = os.path.isfile(os.path.join(project_dir, rel_path))
        return exists, f"{rel_path} {'existe' if exists else 'ausente'}"
    return check


def unittest_ok(rel_path: str):
    """Fábrica de check: roda o arquivo como unittest REALMENTE (subprocess).

    Diferente de checar substring: valida que o teste do modelo roda e passa.
    Timeout curto: teste travado = falha, não bloqueia o benchmark.
    """
    import subprocess
    import sys

    def check(project_dir: str):
        path = os.path.join(project_dir, rel_path)
        if not os.path.isfile(path):
            return False, f"arquivo ausente: {rel_path}"
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "unittest", rel_path[:-3], "-v"],
                cwd=project_dir, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            return False, f"{rel_path} estourou timeout de 30s"
        ok = proc.returncode == 0
        detail = (proc.stderr or proc.stdout or b"").decode(
            "utf-8", errors="replace").strip().splitlines()
        if ok:
            msg = detail[-1] if detail else "ok"
            return True, f"unittest PASSOU: {msg[:120]}"
        # falha: devolve os FAIL:/ERROR: reais para o modelo se autocorrigir
        quebras = [ln.strip() for ln in detail
                   if ln.strip().startswith(("FAIL:", "ERROR:"))]
        msg = "; ".join(quebras[:4]) or (detail[-1] if detail else "falhou")
        return False, f"unittest FALHOU: {msg[:400]}"
    return check


def python_expr_ok(module: str, expr: str):
    """Fábrica de check: importa o módulo do modelo e avalia uma expressão.

    Ex.: expr=\"slugify('Ação') == 'acao'\" → valida COMPORTAMENTO real.
    """
    import subprocess
    import sys

    def check(project_dir: str):
        mod_path = os.path.join(project_dir, f"{module}.py")
        if not os.path.isfile(mod_path):
            return False, f"módulo ausente: {module}.py"
        code = (f"from {module} import *; "
                f"r = {expr}; "
                "print('OK' if r else 'FALSO: ' + " + repr(expr) + ")")
        try:
            proc = subprocess.run(
                [sys.executable, "-c", code],
                cwd=project_dir, capture_output=True, timeout=15)
        except subprocess.TimeoutExpired:
            return False, f"expressão estourou timeout: {expr[:80]}"
        out = (proc.stdout or b"").decode("utf-8", errors="replace").strip()
        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            tail = err.splitlines()[-1] if err.splitlines() else "erro"
            return False, f"{module}: {tail[:120]}"
        ok = "OK" in out and "FALSO" not in out
        return ok, (out[:120] if not ok
                    else f"{module}: {expr[:60]} → PASSOU")
    return check
