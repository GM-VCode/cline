# ============================================================
#  data/mongodb/store/runtime.py — class RuntimePaths
#  Resolve caminhos do runtime (raiz, data/json/, .env) e a
#  configuração de conexão (uri, db, task_id).
# ============================================================

import os

DEFAULT_URI = "mongodb://localhost:27017/"
DEFAULT_DB = "cline_agent"


class RuntimePaths:
    """Caminhos + configuração efetiva do runtime do agente."""

    def __init__(self):
        self.root = self._project_root()
        self.env = self._load_env()
        self.data_dir = os.path.join(self.root, "data", "json")
        os.makedirs(self.data_dir, exist_ok=True)
        self.state_path = os.path.join(self.data_dir, "task-state.json")
        self.validations_path = os.path.join(self.data_dir, "validations.json")
        self.diagnostics_path = os.path.join(self.data_dir, "diagnostics.json")
        self.benchmarks_path = os.path.join(self.data_dir, "benchmarks.json")
        self.agent_runs_path = os.path.join(self.data_dir, "agent_runs.json")
        self.uri = self._setting("MONGODB_URI") or DEFAULT_URI
        self.db_name = self._setting("MONGODB_DB") or DEFAULT_DB
        self.task_id = self._setting("TASK_ID") or "current"

    @staticmethod
    def _project_root() -> str:
        # runtime.py -> store/ -> mongodb/ -> data/ -> RAIZ (4 dirname)
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))))

    @staticmethod
    def _load_env() -> dict[str, str]:
        # reusa o loader central (mesma tolerância, MESMO log de falha
        # em logs/app: .env ilegível nunca passa mais em silêncio)
        from project_path.dotenv import load_dotenv
        return load_dotenv(
            os.path.join(RuntimePaths._project_root(), ".env"))

    def _setting(self, key: str) -> str:
        return self.env.get(key, "") or os.environ.get(key, "")