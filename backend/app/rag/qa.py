"""RAG question answering: retrieve grounded context, then generate an answer.

Ties the retrieval layer to Claude. The anti-hallucination guardrail short-
circuits before any LLM call when no relevant context is found, so the assistant
says "I don't know" instead of inventing an answer (and we don't pay for a
generation we don't want).
"""

from app.bedrock.generation import generate
from app.rag.retrieval import retrieve_with_guardrail

NO_CONTEXT_MESSAGE = (
    "I'm sorry, I don't have information about that in our help documents. "
    "Would you like me to connect you with a human?"
)

SYSTEM_PROMPT = (
    "You are ShopSage's customer support assistant. Answer the user's question "
    "using ONLY the provided context. If the context does not fully answer the "
    "question, say what you can and acknowledge the rest is not covered — never "
    "invent policies, numbers, or facts. Be concise and friendly, and mention "
    "which document your answer comes from."
)


def _format_context(hits):
    blocks = []
    for h in hits:
        header = f"[{h['source']} — {h['section']}]"
        blocks.append(f"{header}\n{h['content']}")
    return "\n\n".join(blocks)


def answer_support_question(conn, question):
    """Return a grounded answer with citations, or a safe fallback.

    Shape: {"answer": str, "citations": list[dict], "grounded": bool}
    """
    hits = retrieve_with_guardrail(conn, question)
    if hits is None:
        return {"answer": NO_CONTEXT_MESSAGE, "citations": [], "grounded": False}

    context = _format_context(hits)
    user_message = f"Context:\n{context}\n\nQuestion: {question}"
    answer = generate(SYSTEM_PROMPT, user_message)

    citations = [
        {"source": h["source"], "section": h["section"], "similarity": round(h["similarity"], 3)}
        for h in hits
    ]
    return {"answer": answer, "citations": citations, "grounded": True}
