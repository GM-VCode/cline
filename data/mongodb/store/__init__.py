# data/mongodb/store — memória do agente (pacote modular)
#
#  Arquivos pequenos, cada um com sua classe:
#    runtime.py     -> class RuntimePaths (paths + config do runtime)
#    json_file.py   -> class JsonFile (I/O JSON tolerante)
#    history.py     -> class HistoryCollection (append/list Mongo+JSON)
#    state.py       -> class StateRepo (estado da tarefa)
#    task_store.py  -> class TaskStore (fachada pública)
#
#  API:  from data.mongodb.store import TaskStore

from data.mongodb.store.task_store import TaskStore  # noqa: F401

__all__ = ["TaskStore"]