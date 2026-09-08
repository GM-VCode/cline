# ============================================================
#  app/services/proxy/runstate/states.py — máquina de estados
#  Modelo de conclusão da indústria (Claude Agent SDK, LangGraph):
#    - um TURNO termina quando o modelo responde texto final
#      SEM tool_calls (finish_reason == "stop");
#    - a TAREFA só vira completed por verificação mecânica
#      (check_ok) OU silêncio (timeout) após o turno final;
#    - um request novo REABRE a conversa: volta a in_progress e
#      registra o evento na timeline — nada se perde.
#  Funções puras (sem I/O): fáceis de testar.
# ============================================================

import time

# ---------- estados ----------
IN_PROGRESS = "in_progress"
TURN_FINISHED = "turn_finished"
COMPLETED = "completed"
FAILED = "failed"

VALID_STATUS = {IN_PROGRESS, TURN_FINISHED, COMPLETED, FAILED}

# depois de um turno finalizado, esse silêncio (s) promove a completed
GRACE_SILENCE_S = 300
# proteção anti-loop: conversa sempre in_progress além disso -> failed
MAX_REQUESTS_LOOP = 200


def _now_str(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))


def base_doc(task_id: str, instruction: str, now: float) -> dict:
    """Doc inicial de uma conversa (1 único por task_id)."""
    return {
        "task_id": task_id,
        "instruction": (instruction or "")[:500],
        "status": IN_PROGRESS,
        "finished": False,
        "requests_count": 0,
        "timeline": [],
        "last_finish_reason": "",
        "created_at": _now_str(now),
        "last_update": _now_str(now),
        "last_seen_at": now,
        "error": "",
    }


def apply_request(doc: dict, nota: str, now: float) -> dict:
    """Request novo do usuário: reabre/toca a conversa (nunca cria nova)."""
    doc = dict(doc or {})
    timeline = list(doc.get("timeline") or [])
    status = doc.get("status") or IN_PROGRESS
    evento = {"ts": _now_str(now), "nota": (nota or "")[:500]}
    if status in (COMPLETED, FAILED):
        evento["tipo"] = "user_reopen"
        evento["detalhe"] = "conversa reaberta por novo pedido"
    else:
        evento["tipo"] = "user_request"
    timeline.append(evento)
    doc.update({
        "status": IN_PROGRESS,
        "finished": False,
        "requests_count": int(doc.get("requests_count", 0)) + 1,
        "timeline": timeline,
        "last_update": _now_str(now),
        "last_seen_at": now,
        "error": "",
    })
    if doc["requests_count"] >= MAX_REQUESTS_LOOP:
        doc["status"] = FAILED
        doc["finished"] = True
        doc["timeline"] = doc["timeline"][:-1] + [
            {"tipo": "loop_limit", "ts": _now_str(now),
             "nota": f"conversa sem concluir ({MAX_REQUESTS_LOOP} requests)"}]
    return doc


def apply_response(doc: dict, finish_reason: str,
                   has_tool_calls: bool, now: float,
                   check_ok: bool | None = None) -> dict:
    """Resposta do modelo: atualiza status conforme o finish_reason."""
    doc = dict(doc or {})
    timeline = list(doc.get("timeline") or [])
    fr = finish_reason or ""
    evento = {"ts": _now_str(now)}
    if has_tool_calls:
        evento["tipo"] = "model_tool"
        evento["nota"] = "modelo pediu ferramenta (turno segue aberto)"
    elif fr == "stop":
        evento["tipo"] = "model_final"
        evento["nota"] = "turno finalizado (texto, sem ferramenta)"
    elif fr == "length":
        evento["tipo"] = "context_limit"
        evento["nota"] = "contexto estourou — turno encerrado à força"
    else:
        evento["tipo"] = "model_partial"
        evento["nota"] = f"resposta sem finish_reason claro ({fr!r})"
    if check_ok is True:
        evento["nota"] += " | verificação (check) OK"
    timeline.append(evento)
    doc["timeline"] = timeline
    doc["last_finish_reason"] = fr
    doc["last_update"] = _now_str(now)
    doc["last_seen_at"] = now

    if check_ok is True:
        # gate de verificação mecânica: única forma de "completed" direto
        doc["status"] = COMPLETED
        doc["finished"] = True
        doc["error"] = ""
        doc["timeline"].append({
            "tipo": "check_ok", "ts": _now_str(now),
            "nota": "verificação passou — marcado completed"})
        return doc
    if has_tool_calls:
        doc["status"] = IN_PROGRESS
        doc["finished"] = False
        return doc
    if fr in ("stop", "length"):
        # turno finalizado, MAS a tarefa NÃO está concluída (honesto)
        doc["status"] = TURN_FINISHED
        doc["finished"] = False
        return doc
    doc["status"] = IN_PROGRESS
    doc["finished"] = False
    return doc


def promote_timeout(doc: dict, now: float,
                    grace_s: float = GRACE_SILENCE_S) -> dict:
    """turn_finished + silêncio >= grace -> completed (sem confirmar nada)."""
    doc = dict(doc or {})
    if doc.get("status") != TURN_FINISHED:
        return doc
    last_seen = doc.get("last_seen_at") or 0
    if now - last_seen < grace_s:
        return doc
    doc["status"] = COMPLETED
    doc["finished"] = True
    doc["timeline"] = list(doc.get("timeline") or []) + [{
        "tipo": "auto_complete", "ts": _now_str(now),
        "nota": f"turno finalizado sem novos requests por {int(grace_s)}s"}]
    doc["last_update"] = _now_str(now)
    return doc