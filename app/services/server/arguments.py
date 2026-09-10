from project_path import Config


class ServerArguments:
    """Monta flags do llama-server a partir da configuração."""

    def build(self, cfg: Config) -> list[str]:
        args = [
            "-m", cfg.MODEL_PATH, "--alias", cfg.ALIAS,
            "--host", cfg.HOST, "--port", str(cfg.PORT),
            "-ngl", str(cfg.NGL), "-c", str(cfg.CTX),
            "-t", str(cfg.THREADS), "-b", str(cfg.BATCH),
            "-ub", str(cfg.UBATCH),
        ]
        self._sampling(args, cfg)
        args += ["-rea", str(cfg.REASONING).lower()]
        if str(cfg.REASONING).lower() == "off" and not cfg.REASONING_PRESERVE:
            args += ["--no-reasoning-preserve"]
        if cfg.FLASH_ATTN in ("on", "off", "auto"):
            args += ["-fa", cfg.FLASH_ATTN]
        args += ["--parallel", str(cfg.PARALLEL)]
        if cfg.KV_CACHE_TYPE:
            args += ["-ctk", cfg.KV_CACHE_TYPE, "-ctv", cfg.KV_CACHE_TYPE]
        if cfg.MM_PROJ_ENABLED:
            args += ["-mm", cfg.MM_PROJ_PATH,
                     "--image-min-tokens", str(cfg.IMG_MIN_TOKENS)]
        return args

    @staticmethod
    def _sampling(args: list[str], cfg: Config) -> None:
        optional = (("--temp", cfg.TEMP), ("--top-k", cfg.TOP_K),
                    ("--top-p", cfg.TOP_P), ("--min-p", cfg.MIN_P),
                    ("--repeat-penalty", cfg.REPEAT_PENALTY),
                    ("--seed", cfg.SEED))
        for flag, value in optional:
            if value is not None:
                args.extend([flag, str(value)])
