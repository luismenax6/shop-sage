"""Chat endpoint: the backend's mouth.

Receives a user message, runs the agent (which routes between catalog search,
RAG support answers, and cart/ticket actions), and returns the reply plus any
citations and a tool-call trace. The conversation `history` round-trips so the
client can continue a multi-turn exchange (e.g. the confirm-before-write flow).
"""

import psycopg
from flask import Blueprint, current_app, jsonify, request
from pgvector.psycopg import register_vector

from app.agent.orchestrator import run_agent

bp = Blueprint("chat", __name__)


def _collect_citations(tool_calls):
    """Pull source/section citations out of any search_documentation results."""
    citations, seen = [], set()
    for tc in tool_calls:
        if tc["name"] != "search_documentation" or tc.get("status") != "executed":
            continue
        for chunk in tc.get("result", {}).get("chunks", []):
            key = (chunk["source"], chunk["section"])
            if key not in seen:
                seen.add(key)
                citations.append(
                    {"source": chunk["source"], "section": chunk["section"], "similarity": chunk["similarity"]}
                )
    return citations


@bp.post("/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = data.get("message")
    if not message:
        return jsonify(error="'message' is required"), 400

    user_id = data.get("user_id", "user_demo")
    confirm = bool(data.get("confirm", False))
    history = data.get("history")

    # One connection per request for now; a pool comes later.
    with psycopg.connect(current_app.config["DATABASE_URL"]) as conn:
        register_vector(conn)  # needed so the RAG tool can read vector columns
        result = run_agent(conn, message, history=history, user_id=user_id, confirm=confirm)

    return jsonify(
        answer=result["answer"],
        citations=_collect_citations(result["tool_calls"]),
        tool_calls=[{"name": t["name"], "status": t["status"]} for t in result["tool_calls"]],
        history=result["messages"],
    )
