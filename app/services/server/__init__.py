import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from project_path import Config, ProjectPath
from tools.logger import AppLogger
from app.services.server.arguments import ServerArguments
from app.services.server.display import ServerDisplay
from app.services.server.validation import ServerValidator

ROOT = ProjectPath.ROOT


class LlamaServer:
    """Fachada pública do ciclo de vida do llama-server."""

    def __init__(self, config: Config) -> None:
        self.cfg = config
        self.log = AppLogger("server")
        self.validator = ServerValidator()
        self.arguments = ServerArguments()

    def validate(self) -> None:
        self.validator.validate(self.cfg)

    def build_args(self) -> list[str]:
        return self.arguments.build(self.cfg)

    def kill_old(self) -> None:
        if self.cfg.KILL_OLD_INSTANCE:
            subprocess.run(["taskkill", "/f", "/im", "llama-server.exe"],
                           capture_output=True)

    def wait_health(self, timeout_s: int) -> bool:
        url = f"http://{self.cfg.HOST}:{self.cfg.PORT}/health"
        deadline = time.time() + timeout_s
        print(f"Aguardando servidor subir (até {timeout_s}s)...")
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=3) as response:
                    if b"ok" in response.read():
                        return True
            except (urllib.error.URLError, OSError):
                pass
            time.sleep(2)
        return False

    def show_config(self, args: list[str]) -> None:
        ServerDisplay.show(args)

    def run(self) -> None:
        self.validate()
        args = self.build_args()
        if self.cfg.SHOW_CONFIG_ON_BOOT:
            self.show_config(args)
        self.kill_old()
        time.sleep(2)
        os.makedirs(self.cfg.LOG_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(self.cfg.LOG_OUT), exist_ok=True)
        os.makedirs(os.path.dirname(self.cfg.LOG_ERR), exist_ok=True)
        print("Iniciando llama-server...")
        self.log.info("iniciando llama-server (PID pendente)")
        with open(self.cfg.LOG_OUT, "w", encoding="utf-8") as out, \
             open(self.cfg.LOG_ERR, "w", encoding="utf-8") as err:
            process = subprocess.Popen(
                [self.cfg.LLAMA_SERVER] + args,
                stdout=out,
                stderr=err,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            print(f"PID: {process.pid}")
            self.log.info(f"llama-server PID {process.pid}")
            if self.wait_health(self.cfg.WAIT_HEALTH_SECONDS):
                self._serve_until_stopped(process)
            else:
                self._report_health_failure(process)

    def _serve_until_stopped(self, process: subprocess.Popen) -> None:
        print(f"PRONTO: http://{self.cfg.HOST}:{self.cfg.PORT}/v1  "
              f"(Model ID: {self.cfg.ALIAS})")
        self.log.info(f"PRONTO: http://{self.cfg.HOST}:{self.cfg.PORT}/v1 "
                      f"(Model ID: {self.cfg.ALIAS})")
        print("Logs: " + self.cfg.LOG_ERR)
        print("Pressione CTRL+C para encerrar o servidor.")
        try:
            process.wait()
        except KeyboardInterrupt:
            print("Encerrando llama-server...")
            self.log.info("encerrando llama-server (CTRL+C)")
            process.terminate()
        code = process.poll()
        if code not in (0, None):
            print(f"llama-server TERMINOU com exit {code}")
            self.log.error(f"llama-server terminou inesperadamente "
                           f"com exit {code} (ver {self.cfg.LOG_ERR})")

    def _report_health_failure(self, process: subprocess.Popen) -> None:
        print("FALHOU — veja as últimas linhas de " + self.cfg.LOG_ERR)
        self.log.error(f"health check falhou após {self.cfg.WAIT_HEALTH_SECONDS}s "
                       f"(ver {self.cfg.LOG_ERR})")
        process.terminate()
        if os.path.isfile(self.cfg.LOG_ERR):
            with open(self.cfg.LOG_ERR, encoding="utf-8", errors="replace") as log:
                for line in log.readlines()[-15:]:
                    print("  |", line.rstrip())
        sys.exit(1)


__all__ = ["LlamaServer", "ROOT"]
