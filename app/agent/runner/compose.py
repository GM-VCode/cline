# ============================================================
#  app/agent/runner/compose.py — class PromptComposer
#  Monta o prompt final: identidade (opcional) + contexto do
#  projeto (opcional) + instrução. Separado do ciclo para o
#  protocolo de ações (11c) reusar sem duplicar.
# ============================================================

from typing import TYPE_CHECKING

from app.agent.context import ProjectContext

if TYPE_CHECKING:  # anotação só para o editor (não roda em runtime)
    from app.agent import AgentIdentity


class PromptComposer:
    """Compõe o prompt enviado ao executor."""

    def __init__(self, use_context: bool = True,
                 identity: "AgentIdentity | None" = None) -> None:
        self.use_context = use_context
        self.identity = identity

    def compose(self, instruction: str, project_dir: str) -> str:
        parts = []
        if self.identity:
            ident = self.identity.to_prompt()
            if ident:
                parts.append(ident)
        if self.use_context:
            parts.append(ProjectContext(project_dir).to_prompt())
        parts.append(f"INSTRUÇÃO: {instruction}")
        prompt = "\n\n".join(parts)
        self._log_size(instruction, len(prompt))
        return prompt

    @staticmethod
    def _log_size(instruction: str, prompt_len: int) -> None:
        """DEBUG do tamanho do prompt em logs/app/agent.log (nunca levanta)."""
        try:
            from app.agent.debug import get_agent_logger
            log = get_agent_logger()
            if log:
                log.debug(f"prompt composto: {prompt_len}ch "
                          f"(instrução={len(instruction)}ch)")
        except Exception:  # pragma: no cover — logging nunca quebra o compose
            pass
