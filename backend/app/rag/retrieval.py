"""RAG retrieval over the pgvector store, with C-accelerated exact re-scoring.

Two-stage retrieval:
  1. pgvector + HNSW does fast approximate nearest-neighbour search to fetch a
     candidate pool (cheap, scales to millions of rows).
  2. The `csim` C extension recomputes the exact cosine similarity for that pool
     (~65x faster than pure Python). Those exact scores drive the final ranking
     and the anti-hallucination guardrail.

The connection passed in must have had pgvector registered
(`pgvector.psycopg.register_vector(conn)`) so the `embedding` column comes back
as a numeric array rather than a string.
"""

import array

import csim
from psycopg.rows import dict_row

from app.bedrock.embeddings import embed

# Minimum cosine similarity for a chunk to count as relevant.
SIMILARITY_THRESHOLD = 0.25
# Candidate pool fetched from pgvector before exact C re-scoring.
CANDIDATE_POOL = 10


def retrieve(conn, question, k=3):
    """Return the k most similar chunks to `question`, re-scored exactly in C."""
    qvec = embed(question)
    q_buf = array.array("d", qvec)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT content,
                   source,
                   metadata->>'doc_title' AS doc_title,
                   metadata->>'section'   AS section,
                   embedding
            FROM document_chunks
            ORDER BY embedding <=> %s::vector
            LIMIT %s
            """,
            (qvec, CANDIDATE_POOL),
        )
        candidates = cur.fetchall()

    # stage 2: exact cosine in C; its output is what the app acts on
    for c in candidates:
        c["similarity"] = csim.cosine(q_buf, array.array("d", c["embedding"]))
        del c["embedding"]  # don't leak the raw vector to callers

    candidates.sort(key=lambda c: c["similarity"], reverse=True)
    return candidates[:k]


def retrieve_with_guardrail(conn, question, k=3):
    """Like retrieve(), but returns None when no chunk is relevant enough."""
    hits = retrieve(conn, question, k)
    if not hits or hits[0]["similarity"] < SIMILARITY_THRESHOLD:
        return None
    return hits
