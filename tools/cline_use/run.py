import argparse
import json
import os
import shutil
import sys
import tempfile
import urllib.request
from datetime import datetime

for _s in (sys.stdout, sys.stderr):
    _r = getattr(_s, "reconfigure", None)
    if callable(_r):
        _r(encoding="utf-8", errors="replace")

# Execução como script: garante a raiz do projeto no sys.path
_ROOT = __file__[:__file__.rfind("\\tools")] if "\\tools" in __file__ else "."
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from project_path import Config  # noqa: E402
from tools.cline_use.grader import Grader  # noqa: E402
from tools.cline_use.tasks import TASKS, ClineUseTask  # noqa: E402


def _log(level: str, msg: str) -> None:
    """Loga em logs/model/cline-use.log (import lazy, nunca levanta)."""
    try:
        from app.agent.debug import get_cline_use_logger
        log = get_cline_use_logger()
        if log:
            log.log(level, msg)
    except Exception:  # pragma: no cover — logging nunca quebra o bench
        pass

SYSTEM = (
    "Voce e um agente de codigo que usa as ferramentas do Cline "
    "(write de arquivos). Responda APENAS com JSON valido, sem markdown:\n"
    '{"files": {"caminho/relativo.py": "conteudo completo do arquivo"}}\n'
    "Regras: pacotes Python SEMPRE precisam de __init__.py; exporte as "
    "classes publicas no __init__.py (re-export); use classes e type hints."
)


def ask_model(url: str, instruction: str) -> dict:
    """Chama o /v1/chat/completions e extrai o JSON da resposta."""
    payload = json.dumps({
        "model": "local", "temperature": 0.2, "stream": False,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": instruction}],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/v1/chat/completions", data=payload,
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.load(resp)
    texto = body["choices"][0]["message"]["content"]
    inicio, fim = texto.find("{"), texto.rfind("}")
    if inicio < 0 or fim <= inicio:
        raise ValueError(f"resposta sem JSON: {texto[:120]!r}")
    return json.loads(texto[inicio:fim + 1])


def run_task(task: ClineUseTask, url: str, retries: int) -> tuple[
        str, list[tuple[str, bool, str]], dict, int]:
    """Executa uma tarefa; retorna (id, resultados, resposta, tentativas)."""
    project = tempfile.mkdtemp(prefix=f"cline_use_{task.id}_")
    try:
        # Projeto pré-quebrado: grava os seeds ANTES de chamar o modelo
        for path, content in task.seed_files.items():
            full = os.path.join(project, *path.split("/"))
            os.makedirs(os.path.dirname(full) or project, exist_ok=True)
            with open(full, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
        results: list[tuple[str, bool, str]] = []
        resposta: dict = {}
        tentativas = 0
        ultimo_erro = ""
        for attempt in range(1, retries + 1):
            tentativas = attempt
            try:
                resposta = ask_model(url, task.instruction)
            except Exception as exc:  # noqa: BLE001 — vira tentativa falha
                ultimo_erro = str(exc)[:300]
                results = []
                print(f"  [tentativa {attempt}] resposta invalida: {ultimo_erro}")
                _log("ERROR", f"run {task.id} tentativa {attempt} falhou: "
                              f"{ultimo_erro}")
                continue
            files = {p: c for p, c in resposta.get("files", {}).items()
                     if isinstance(p, str) and isinstance(c, str)}
            for path, content in files.items():
                full = os.path.join(project, *path.replace("\\", "/").split("/"))
                os.makedirs(os.path.dirname(full) or project, exist_ok=True)
                with open(full, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
            results = Grader(project).grade(task, files)
            if all(ok for _, ok, _ in results):
                return task.id, results, resposta, tentativas
            falhas = "\n".join(f"FAIL {n}: {d}" for n, ok, d in results if not ok)
            task = ClineUseTask(**{**task.__dict__,
                                   "instruction": task.instruction +
                                   f"\n\nSua tentativa anterior falhou:\n{falhas}\n"
                                   "Corrija e reenvie o JSON completo."})
        if not results:
            return (task.id,
                    [("resposta_json", False,
                      f"todas as tentativas falharam: {ultimo_erro}")],
                    resposta, tentativas)
        return task.id, results, resposta, tentativas
    finally:
        shutil.rmtree(project, ignore_errors=True)


def bench_log_path() -> str:
    """Caminho do log desta corrida: logs\\model\\<MODELO>_<timestamp>.log.
    Usa o nome único do modelo (igual à chave no Mongo), não o ALIAS."""
    arquivo = os.path.splitext(os.path.basename(Config().MODEL_PATH))[0]
    modelo = arquivo.split("-")[-1].strip() or "unknown"
    ts = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    pasta = os.path.join(_ROOT, "logs", "model")
    os.makedirs(pasta, exist_ok=True)
    return os.path.join(pasta, f"{modelo}_{ts}.log")


class Tee:
    """Escreve no console E no log da corrida."""

    def __init__(self, caminho: str) -> None:
        self.arquivo = open(caminho, "a", encoding="utf-8")

    def print(self, *args: object) -> None:
        linha = " ".join(str(a) for a in args)
        print(linha)
        self.arquivo.write(linha + "\n")
        self.arquivo.flush()

    def close(self) -> None:
        self.arquivo.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bench de uso das ferramentas Cline: pontua e mostra onde o modelo erra")
    parser.add_argument("--url", default="http://127.0.0.1:8081")
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args()

    log_path = bench_log_path()
    saida = Tee(log_path)
    total_ok = total = 0
    for task in TASKS:
        saida.print(f"\n=== {task.id} ===")
        try:
            tid, results, _, tent = run_task(task, args.url, args.retries)
        except Exception as exc:  # noqa: BLE001 — relatório não deve abortar
            saida.print(f"ERRO: {exc}")
            _log("ERROR", f"run {task.id} estourou exceção: {exc}")
            continue
        saida.print(f" tentativas usadas: {tent}/{args.retries}")
        for nome, ok, detalhe in results:
            icon = "✅" if ok else "❌"
            saida.print(f" {icon} {nome:<18} {detalhe}")
        total += len(results)
        total_ok += sum(1 for _, ok, _ in results if ok)
    saida.print(f"\nPONTUACAO: {total_ok}/{total} checks "
                f"({100 * total_ok // max(total, 1)}%)")
    saida.close()
    _log("INFO" if total_ok == total else "WARN",
         f"corrida cline_use: {total_ok}/{total} checks "
         f"(log da corrida: {log_path})")
    print(f"\nLog da corrida: {log_path}")
    return 0 if total_ok == total else 1


if __name__ == "__main__":
    sys.exit(main())
