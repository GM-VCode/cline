# ============================================================
#  server.py — inicia o llama-server lendo server_config.py
#  Você não precisa editar este arquivo; edite server_config.py
# ============================================================
import os
import sys
import time
import subprocess
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server_config as cfg


def build_args() -> list:
    """Monta a lista de argumentos do llama-server a partir da config."""
    args = [
        "-m", cfg.MODEL_PATH,
        "--alias", cfg.ALIAS,
        "--host", cfg.HOST,
        "--port", str(cfg.PORT),
        "-ngl", str(cfg.NGL),
        "-c", str(cfg.CTX),
        "-t", str(cfg.THREADS),
        "-b", str(cfg.BATCH),
        "-ub", str(cfg.UBATCH),
    ]
    if cfg.TEMP is not None:
        args += ["--temp", str(cfg.TEMP)]
    if cfg.TOP_K is not None:
        args += ["--top-k", str(cfg.TOP_K)]
    if cfg.TOP_P is not None:
        args += ["--top-p", str(cfg.TOP_P)]
    if cfg.MIN_P is not None:
        args += ["--min-p", str(cfg.MIN_P)]
    if cfg.REPEAT_PENALTY is not None:
        args += ["--repeat-penalty", str(cfg.REPEAT_PENALTY)]
    if cfg.SEED is not None:
        args += ["--seed", str(cfg.SEED)]
    # VISION: carrega o módulo de visão (-mm) se estiver ativo
    if cfg.MM_PROJ_ENABLED:
        args += ["-mm", cfg.MM_PROJ_PATH]
        # Mínimo de tokens por imagem (Qwen-VL precisa de ao menos 1024 para precisão)
        args += ["--image-min-tokens", str(cfg.IMG_MIN_TOKENS)]
    return args


def kill_old() -> None:
    if not cfg.KILL_OLD_INSTANCE:
        return
    subprocess.run(
        ["taskkill", "/f", "/im", "llama-server.exe"],
        capture_output=True,
    )


def validate() -> None:
    """Validações básicas para falhar cedo com mensagens claras."""
    problems = []
    if not os.path.isfile(cfg.LLAMA_SERVER):
        problems.append(f"llama-server.exe não encontrado: {cfg.LLAMA_SERVER}")
    if not os.path.isfile(cfg.MODEL_PATH):
        problems.append(f"Modelo não encontrado: {cfg.MODEL_PATH}")
    if cfg.MM_PROJ_ENABLED and cfg.MM_PROJ_PATH:
        if not os.path.isfile(cfg.MM_PROJ_PATH):
            problems.append(
                f"Módulo de visão ativo (MM_PROJ_ENABLED=1) mas não encontrado: {cfg.MM_PROJ_PATH}"
            )
    elif cfg.MM_PROJ_ENABLED:
        problems.append("MM_PROJ_ENABLED=1 pero MM_PROJ_PATH está vazio")
    if cfg.CTX % 256 != 0:
        problems.append(f"CTX ({cfg.CTX}) deveria ser múltiplo de 256")
    for name, val in (("TOP_K", cfg.TOP_K), ("TOP_P", cfg.TOP_P), ("MIN_P", cfg.MIN_P)):
        if val is not None and val <= 0:
            problems.append(f"{name} deve ser positivo (recebido: {val})")
    if problems:
        print("ERROS NA CONFIGURAÇÃO:")
        for p in problems:
            print("  -", p)
        sys.exit(1)


def show_config(args: list) -> None:
    print("=" * 60)
    print("  Qwythos-9B — config efetiva")
    print("=" * 60)
    for i in range(0, len(args), 2):
        print(f"  {args[i]:<16} {args[i + 1]}")
    print("=" * 60)


def wait_health(timeout_s: int) -> bool:
    url = f"http://{cfg.HOST}:{cfg.PORT}/health"
    deadline = time.time() + timeout_s
    print(f"Aguardando servidor subir (até {timeout_s}s)...")
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as r:
                if b"ok" in r.read():
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(2)
    return False


def main() -> None:
    validate()
    args = build_args()
    if cfg.SHOW_CONFIG_ON_BOOT:
        show_config(args)

    kill_old()
    time.sleep(2)

    print("Iniciando llama-server...")
    with open(cfg.LOG_OUT, "w", encoding="utf-8") as out, \
         open(cfg.LOG_ERR, "w", encoding="utf-8") as err:
        proc = subprocess.Popen(
            [cfg.LLAMA_SERVER] + args,
            stdout=out,
            stderr=err,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        print(f"PID: {proc.pid}")

        if wait_health(cfg.WAIT_HEALTH_SECONDS):
            print(f"PRONTO: http://{cfg.HOST}:{cfg.PORT}/v1  (Model ID: {cfg.ALIAS})")
            print("Logs: " + cfg.LOG_ERR)
            print("Pressione CTRL+C para encerrar o servidor.")
            try:
                proc.wait()
            except KeyboardInterrupt:
                print("Encerrando llama-server...")
                proc.terminate()
        else:
            print("FALHOU — veja as últimas linhas de " + cfg.LOG_ERR)
            proc.terminate()
            if os.path.isfile(cfg.LOG_ERR):
                with open(cfg.LOG_ERR, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                for line in lines[-15:]:
                    print("  |", line.rstrip())
            sys.exit(1)


if __name__ == "__main__":
    main()
