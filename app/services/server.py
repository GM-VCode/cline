# ============================================================
#  app/server.py — classe LlamaServer
#  Valida a config, monta os argumentos e executa o
#  llama-server. Configure tudo pelo .env (não aqui).
# ============================================================

import os
import sys
import time
import subprocess
import urllib.request
import urllib.error

from project_path import Config, ProjectPath
from tools.logger import AppLogger

# alias de compatibilidade (testes e código antigo usam server.ROOT)
ROOT = ProjectPath.ROOT


class LlamaServer:
    """Encapsula todo o ciclo de vida do processo llama-server."""

    def __init__(self, config: Config) -> None:
        self.cfg = config
        self.log = AppLogger("server")

    # ---------- validação ----------
    def validate(self) -> None:
        """Falha cedo com mensagens claras se algo estiver errado."""
        problems = []
        c = self.cfg
        if not os.path.isfile(c.LLAMA_SERVER):
            problems.append(f"llama-server.exe não encontrado: {c.LLAMA_SERVER}")
        if not c.MODEL_PATH:
            problems.append(
                "MODEL_PATH vazio: não encontrei UM único .gguf em "
                f"{ProjectPath.MODELS_DIR} (tenha exatamente 1 modelo "
                "na pasta, ou defina MODEL_PATH no .env)")
        elif not os.path.isfile(c.MODEL_PATH):
            problems.append(f"Modelo não encontrado: {c.MODEL_PATH}")
            try:
                exist = [f for f in os.listdir(ProjectPath.MODELS_DIR)
                         if f.lower().endswith(".gguf")]
                if exist:
                    problems.append(
                        "Modelos disponíveis em "
                        f"{ProjectPath.MODELS_DIR}: {', '.join(exist)}")
            except OSError:
                pass
        if c.MM_PROJ_ENABLED and c.MM_PROJ_PATH:
            if not os.path.isfile(c.MM_PROJ_PATH):
                problems.append(
                    f"Módulo de visão ativo (MM_PROJ_ENABLED=1) mas não encontrado: {c.MM_PROJ_PATH}"
                )
        elif c.MM_PROJ_ENABLED:
            problems.append("MM_PROJ_ENABLED=1 mas MM_PROJ_PATH está vazio")
        if c.CTX % 256 != 0:
            problems.append(f"CTX ({c.CTX}) deveria ser múltiplo de 256")
        if str(c.REASONING).lower() not in ("on", "off", "auto"):
            problems.append(
                f"REASONING inválido: {c.REASONING} (use on | off | auto)")
        for name, val in (("TOP_K", c.TOP_K), ("TOP_P", c.TOP_P), ("MIN_P", c.MIN_P)):
            if val is not None and val <= 0:
                problems.append(f"{name} deve ser positivo (recebido: {val})")
        if problems:
            print("ERROS NA CONFIGURAÇÃO:")
            for p in problems:
                print("  -", p)
            sys.exit(1)

    # ---------- argumentos ----------
    def build_args(self) -> list[str]:
        """Monta a lista de argumentos do llama-server a partir da config."""
        c = self.cfg
        args = [
            "-m", c.MODEL_PATH,
            "--alias", c.ALIAS,
            "--host", c.HOST,
            "--port", str(c.PORT),
            "-ngl", str(c.NGL),
            "-c", str(c.CTX),
            "-t", str(c.THREADS),
            "-b", str(c.BATCH),
            "-ub", str(c.UBATCH),
        ]
        if c.TEMP is not None:
            args += ["--temp", str(c.TEMP)]
        if c.TOP_K is not None:
            args += ["--top-k", str(c.TOP_K)]
        if c.TOP_P is not None:
            args += ["--top-p", str(c.TOP_P)]
        if c.MIN_P is not None:
            args += ["--min-p", str(c.MIN_P)]
        if c.REPEAT_PENALTY is not None:
            args += ["--repeat-penalty", str(c.REPEAT_PENALTY)]
        if c.SEED is not None:
            args += ["--seed", str(c.SEED)]
        # RACIOCÍNIO (<think>): -rea on|off|auto. Default "off" p/ o Cline
        # (thinking ligado truncava tool calls longos e degradava a saída)
        args += ["-rea", str(c.REASONING).lower()]
        # FLASH ATTENTION: reduz a VRAM do KV cache (crítico p/ 16 GB)
        if c.FLASH_ATTN in ("on", "off", "auto"):
            args += ["-fa", c.FLASH_ATTN]
        # PARALLEL: nº de slots — 1 concentra todo o CTX (uso solo no Cline)
        args += ["--parallel", str(c.PARALLEL)]
        # KV CACHE QUANTIZADA: q8_0 = ~metade da VRAM com perda mínima
        if c.KV_CACHE_TYPE:
            args += ["-ctk", c.KV_CACHE_TYPE, "-ctv", c.KV_CACHE_TYPE]
        # VISION: carrega o módulo de visão (-mm) se estiver ativo
        if c.MM_PROJ_ENABLED:
            args += ["-mm", c.MM_PROJ_PATH]
            # Mínimo de tokens por imagem (Qwen-VL: ao menos 1024 p/ precisão)
            args += ["--image-min-tokens", str(c.IMG_MIN_TOKENS)]
        return args


    # ---------- processo antigo ----------
    def kill_old(self) -> None:
        if not self.cfg.KILL_OLD_INSTANCE:
            return
        subprocess.run(
            ["taskkill", "/f", "/im", "llama-server.exe"],
            capture_output=True,
        )

    # ---------- saúde ----------
    def wait_health(self, timeout_s: int) -> bool:
        url = f"http://{self.cfg.HOST}:{self.cfg.PORT}/health"
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

    # ---------- exibição ----------
    def show_config(self, args: list[str]) -> None:
        print("=" * 60)
        print("  Qwythos-9B — config efetiva")
        print("=" * 60)
        for i in range(0, len(args), 2):
            print(f"  {args[i]:<16} {args[i + 1]}")
        print("=" * 60)

    # ---------- execução ----------
    def run(self) -> None:
        c = self.cfg
        self.validate()
        args = self.build_args()
        if c.SHOW_CONFIG_ON_BOOT:
            self.show_config(args)

        self.kill_old()
        time.sleep(2)

        # Asegurar que logs/ exista (logs centralizados del proyecto)
        os.makedirs(c.LOG_DIR, exist_ok=True)

        print("Iniciando llama-server...")
        self.log.info("iniciando llama-server (PID pendiente)")
        with open(c.LOG_OUT, "w", encoding="utf-8") as out, \
             open(c.LOG_ERR, "w", encoding="utf-8") as err:
            proc = subprocess.Popen(
                [c.LLAMA_SERVER] + args,
                stdout=out,
                stderr=err,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            print(f"PID: {proc.pid}")
            self.log.info(f"llama-server PID {proc.pid}")

            if self.wait_health(c.WAIT_HEALTH_SECONDS):
                print(f"PRONTO: http://{c.HOST}:{c.PORT}/v1  (Model ID: {c.ALIAS})")
                self.log.info(f"PRONTO: http://{c.HOST}:{c.PORT}/v1 "
                              f"(Model ID: {c.ALIAS})")
                print("Logs: " + c.LOG_ERR)
                print("Pressione CTRL+C para encerrar o servidor.")
                try:
                    proc.wait()
                except KeyboardInterrupt:
                    print("Encerrando llama-server...")
                    self.log.info("encerrando llama-server (CTRL+C)")
                    proc.terminate()
            else:
                print("FALHOU — veja as últimas linhas de " + c.LOG_ERR)
                self.log.error(f"health check falhou tras {c.WAIT_HEALTH_SECONDS}s "
                               f"(ver {c.LOG_ERR})")
                proc.terminate()
                if os.path.isfile(c.LOG_ERR):
                    with open(c.LOG_ERR, encoding="utf-8", errors="replace") as f:
                        lines = f.readlines()
                    for line in lines[-15:]:
                        print("  |", line.rstrip())
                sys.exit(1)
