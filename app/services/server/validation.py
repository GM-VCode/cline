import os
import sys

from project_path import Config, ProjectPath


class ServerValidator:
    """Valida caminhos e parâmetros antes de iniciar o llama-server."""

    def validate(self, cfg: Config) -> None:
        problems: list[str] = []
        if not os.path.isfile(cfg.LLAMA_SERVER):
            problems.append(f"llama-server.exe não encontrado: {cfg.LLAMA_SERVER}")
        self._validate_model(cfg, problems)
        self._validate_mmproj(cfg, problems)
        self._validate_numeric(cfg, problems)
        self._validate_reasoning(cfg, problems)
        if problems:
            print("ERROS NA CONFIGURAÇÃO:")
            for problem in problems:
                print("  -", problem)
            sys.exit(1)

    def _validate_model(self, cfg: Config, problems: list[str]) -> None:
        if not cfg.MODEL_PATH:
            problems.append(
                "MODEL_PATH vazio: não encontrei UM único .gguf em "
                f"{ProjectPath.MODELS_DIR} (tenha exatamente 1 modelo "
                "na pasta, ou defina MODEL_PATH no .env)"
            )
        elif not os.path.isfile(cfg.MODEL_PATH):
            problems.append(f"Modelo não encontrado: {cfg.MODEL_PATH}")
            try:
                models = [name for name in os.listdir(ProjectPath.MODELS_DIR)
                          if name.lower().endswith(".gguf")]
                if models:
                    problems.append(
                        f"Modelos disponíveis em {ProjectPath.MODELS_DIR}: "
                        + ", ".join(models)
                    )
            except OSError:
                pass

    @staticmethod
    def _validate_mmproj(cfg: Config, problems: list[str]) -> None:
        if cfg.MM_PROJ_ENABLED and cfg.MM_PROJ_PATH:
            if not os.path.isfile(cfg.MM_PROJ_PATH):
                problems.append(
                    "Módulo de visão ativo (MM_PROJ_ENABLED=1) mas não "
                    f"encontrado: {cfg.MM_PROJ_PATH}"
                )
        elif cfg.MM_PROJ_ENABLED:
            problems.append("MM_PROJ_ENABLED=1 mas MM_PROJ_PATH está vazio")

    @staticmethod
    def _validate_numeric(cfg: Config, problems: list[str]) -> None:
        if cfg.CTX % 256 != 0:
            problems.append(f"CTX ({cfg.CTX}) deveria ser múltiplo de 256")
        for name, value in (("TOP_K", cfg.TOP_K), ("TOP_P", cfg.TOP_P),
                            ("MIN_P", cfg.MIN_P)):
            if value is not None and value <= 0:
                problems.append(f"{name} deve ser positivo (recebido: {value})")

    @staticmethod
    def _validate_reasoning(cfg: Config, problems: list[str]) -> None:
        if str(cfg.REASONING).lower() not in ("on", "off", "auto"):
            problems.append(
                f"REASONING inválido: {cfg.REASONING} (use on | off | auto)"
            )
