# ============================================================
#  app/agent/runner/compose.py — class PromptComposer
#  Monta o prompt final: identidade (opcional) + contexto do
#  projeto (opcional) + instrução. Separado do ciclo para o
#  protocolo de ações (11c) reusar sem duplicar.
# ============================================================

from app.agent.context import ProjectContext


class PromptComposer:
    """Compõe o prompt enviado ao executor."""

    def __init__(self, use_context: bool = True, identity=None):
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
        return "\n\n".join(parts)
