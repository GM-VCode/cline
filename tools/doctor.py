# ============================================================
#  doctor.py — class ModelDoctor
#  Ferramenta de diagnóstico: rode quando notar algo estranho
#  no modelo/ambiente. Checa config, paths, logs, JSON de estado,
#  Mongo, memória do agente e servidor/API (sem subir modelo).
#  Salva relatório em Mongo (diagnostics) ou JSON fallback.
#
#  Uso:  python doctor.py
# ============================================================

import os
import sys
import urllib.request
import urllib.error
from typing import Any, cast

# Emojis nos prints: garante stdout UTF-8 mesmo em consoles
# Windows cp1252 e pipes (recuperação de falha de shell).
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # pragma: no cover
            pass

# doctor.py -> tools/ -> RAIZ (2 dirname)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from project_path import Config, ProjectPath  # noqa: E402
ProjectPath.ensure()

from data.mongodb.store import TaskStore  # noqa: E402
from tools.logger import AppLogger  # noqa: E402

ICONS = {"ok": "✅", "warn": "⚠️ ", "fail": "❌"}


class ModelDoctor:
    """Diagnóstico do ambiente do modelo/agente (checks pequenos)."""

    def __init__(self, cfg: Config, store: TaskStore | None = None) -> None:
        self.cfg = cfg
        self.store = store
        self.log = AppLogger("doctor")
        self.results: list[dict[str, str]] = []

    def _add(self, status: str, name: str, msg: str) -> None:
        self.results.append({"check": name, "status": status, "detail": msg})

    def check_paths(self) -> tuple[str, str]:
        c = self.cfg
        msgs: list[str] = []
        if not os.path.isfile(c.LLAMA_SERVER):
            msgs.append(f"llama-server.exe ausente: {c.LLAMA_SERVER}")
        if not os.path.isfile(c.MODEL_PATH):
            msgs.append(f"modelo ausente: {c.MODEL_PATH}")
        if c.MM_PROJ_ENABLED and not os.path.isfile(c.MM_PROJ_PATH):
            msgs.append(f"mmproj ausente: {c.MM_PROJ_PATH}")
        if msgs:
            return ("fail", "; ".join(msgs))
        size = os.path.getsize(c.MODEL_PATH) / 1e9
        return ("ok", f"modelo {size:.1f}GB + llama-server ok")

    def check_config(self) -> tuple[str, str]:
        c = self.cfg
        probs: list[str] = []
        if c.CTX % 256 != 0:
            probs.append(f"CTX={c.CTX} não é múltiplo de 256")
        if str(c.LOG_LEVEL).upper() not in ("DEBUG", "INFO", "WARN", "ERROR", "CRITICAL"):
            probs.append(f"LOG_LEVEL inválido: {c.LOG_LEVEL}")
        if probs:
            return ("fail", "; ".join(probs))
        return ("ok", f"CTX={c.CTX}, LOG_LEVEL={c.LOG_LEVEL}")

    def check_logs(self) -> tuple[str, str]:
        try:
            os.makedirs(self.cfg.LOG_DIR, exist_ok=True)
            probe = os.path.join(self.cfg.LOG_DIR, ".probe.tmp")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
        except OSError as exc:
            return ("fail", f"logs/ não é gravável: {exc}")
        has = os.path.isfile(self.cfg.APP_LOG)
        return ("ok", f"logs/ gravável; app.log {'existe' if has else 'vazio ainda'}")

    def check_state_json(self) -> tuple[str, str]:
        from data.mongodb.store.json_file import JsonFile
        paths = getattr(self.store, "paths", None)
        state_path = paths.state_path if paths else ""
        if state_path and os.path.isfile(state_path):
            data = JsonFile.read(state_path)
            if isinstance(data, dict):
                state: dict[str, Any] = cast(dict[str, Any], data)
                return (
                    "ok",
                    f"estado legível (atualizado {state.get('updated_at', '?')})",
                )
            return ("fail", f"JSON de estado corrompido: {state_path}")
        return ("ok", "sem estado em disco ainda (normal em repo novo)")
    def check_mongo(self) -> tuple[str, str]:
        if self.store is None:
            return ("warn", "TaskStore indisponível")
        if self.store.active:
            return ("ok", f"Mongo OK (db={self.store.db_name})")
        return ("warn", f"Mongo indisponível (fallback JSON): {self.store.error}")

    def check_memory(self) -> tuple[str, str]:
        state = self.store.load_state() if self.store else {}
        if not state:
            return ("warn", "memória vazia: nenhuma tarefa registrada ainda")
        return ("ok", f"task_id={state.get('task_id', '?')}, "
                      f"etapas={len(state.get('plan', []))}, "
                      f"atualizado={state.get('updated_at', '?')}")

    def check_server(self) -> tuple[str, str]:
        c = self.cfg
        url = f"http://{c.HOST}:{c.PORT}/health"
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                body = r.read().decode("utf-8", "replace")
            return ("ok", f"servidor no ar: {url} -> {body.strip()[:40]}")
        except (urllib.error.URLError, OSError):
            return ("warn", f"servidor NÃO está rodando em {url} "
                            f"(ok se foi encerrado de propósito)")

    def _run_checks(self, verbose: bool = True) -> tuple[int, int]:
        checks = [
            ("paths", self.check_paths), ("config", self.check_config),
            ("logs", self.check_logs), ("state_json", self.check_state_json),
            ("mongo", self.check_mongo), ("memoria", self.check_memory),
            ("servidor_api", self.check_server),
        ]
        fails = warns = 0
        if verbose:
            print("=" * 62)
            print("  DOCTOR — diagnóstico do modelo/ambiente")
            print("=" * 62)
        for name, fn in checks:
            try:
                status, msg = fn()
            except Exception as exc:  # pragma: no cover
                status, msg = "fail", f"exceção: {exc}"
                self.log.error(f"check {getattr(fn, '__name__', fn)!r} "
                               f"estourou exceção: {exc}")
            fails += status == "fail"
            warns += status == "warn"
            if verbose:
                print(f"  {ICONS[status]} {name:<12} {msg}")
            self._add(status, name, msg)
        return fails, warns

    def run(self, save: bool = True, verbose: bool = True) -> int:
        fails, warns = self._run_checks(verbose=verbose)
        verdict = "SAUDAVEL" if fails == 0 else "PROBLEMAS ENCONTRADOS"
        if verbose:
            print(f"  resultado: {verdict} ({fails} falha(s), {warns} aviso(s))")
        self.log.info(f"doctor: {verdict} (fails={fails}, warns={warns})")
        if save and self.store is not None:
            self.store.append_diagnostic({
                "verdict": verdict, "fails": fails, "warns": warns,
                "checks": self.results,
            })
        return 1 if fails else 0


def main() -> int:
    return ModelDoctor(Config(), TaskStore()).run()


if __name__ == "__main__":
    sys.exit(main())