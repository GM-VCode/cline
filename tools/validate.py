# ============================================================
#  validate.py — GATE DE VALIDACIÓN OBLIGATORIO
#
#  Un solo comando que el agente DEBE ejecutar antes de declarar
#  una tarea concluida. Corre, en orden:
#    1) sintaxis (compileall)
#    2) tests unitarios (unittest, stdlib)
#    3) sanity del diff (git diff --check, tolerante a ausencia de git)
#
#  Para en la primera fase que falle y explica QUÉ falló y cómo
#  repetir. Exit 0 = listo para concluir; exit 1 = hay que corregir.
#
#  Uso:  python validate.py
# ============================================================

import os
import subprocess
import sys

# validate.py -> tools/ -> RAIZ (2 dirname)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from project_path import ProjectPath  # noqa: E402
ProjectPath.ensure()

# alias usado por main() (targets de compileall)
ROOT = ProjectPath.ROOT


def _run(cmd: list[str]) -> tuple[int, str]:
    """Ejecuta un comando y devuelve (código, salida)."""
    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out.strip()


def step(nome: str, cmd: list[str], on_fail: str) -> bool:
    print(f"==> {nome}")
    code, out = _run(cmd)
    if out:
        print(out)
    if code != 0:
        print(f"    [FALLO] {nome}")
        print(f"    -> {on_fail}")
        return False
    print("    [OK]")
    return True


def main() -> int:
    targets = [
        os.path.join(ROOT, "app"),
        os.path.join(ROOT, "main.py"),
        os.path.join(ROOT, "tools"),
        os.path.join(ROOT, "tests"),
        os.path.join(ROOT, "data", "mongodb"),
    ]

    # 1) Sintaxis
    if not step(
        "Sintaxis (compileall)",
        [sys.executable, "-m", "compileall", "-q"] + targets,
        "Erro de sintaxis/import; revisa o archivo indicado arriba.",
    ):
        return 1

    # 2) Tests unitarios
    if not step(
        "Tests unitarios (unittest)",
        [sys.executable, "-m", "unittest", "discover", "-s",
         os.path.join(ROOT, "tests"), "-v"],
        "Hai tests em vermelho; corrige a causa raiz antes de concluir.",
    ):
        return 1

    # 3) Sanity del diff (whitespace / marcadores de conflicto)
    if os.path.isdir(os.path.join(ROOT, ".git")):
        if not step(
            "git diff --check",
            ["git", "diff", "--check"],
            "Whitespace ou marcadores de conflicto no diff; corege-os.",
        ):
            return 1
    else:
        print("==> git diff --check")
        print("    [SKIP] não é un repo git")

    print("\nVALIDACIÓN COMPLETA: TODO OK.")
    return 0


if __name__ == "__main__":
    rc = main()
    # Registrar la corrida de validación en el histórico (Mongo local + JSON).
    # Nunca debe romper el flujo si Mongo no está disponible.
    try:
        from app.task_store import TaskStore
        store = TaskStore()
        store.append_validation({
            "phase": "validate",
            "result": "ok" if rc == 0 else "fail",
            "exit_code": rc,
        })
        store.close()
    except Exception:
        pass
    # Log a logs/app.log (capa de logging centralizada del proyecto)
    try:
        from tools.logger import AppLogger
        AppLogger("validate").log(
            "INFO" if rc == 0 else "ERROR",
            f"validate terminó con exit {rc}",
        )
    except Exception:
        pass
    sys.exit(rc)