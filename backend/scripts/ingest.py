"""Ingest policy documents into the RAG vector store.

Pipeline:  data/policies/*.md  ->  chunk by section  ->  embed (Bedrock Titan v2)
           ->  upsert into document_chunks

Idempotent: each document's chunks are deleted and reinserted on every run, so
re-running after editing a document leaves a clean, consistent state.

Usage:
    cd backend && source .venv/bin/activate
    python scripts/ingest.py
"""

import json
import os
import re
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

# make backend/ importable so this script can use the shared app modules
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.bedrock.embeddings import embed  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICIES_DIR = REPO_ROOT / "data" / "policies"

MAX_CHARS = 1500  # soft cap per chunk; longer sections are split by paragraph


# ---------------------------------------------------------------------------
# 1. Chunking
# ---------------------------------------------------------------------------
def chunk_markdown(text):
    """Split a markdown doc into (section_title, content) chunks.

    Splits on level-2 headings (## ). The document's level-1 title (# ) is
    prepended to every chunk's content so each embedding carries context.
    """
    lines = text.splitlines()

    doc_title = "Untitled"
    if lines and lines[0].startswith("# "):
        doc_title = lines[0][2:].strip()

    # split the body into sections keyed by "## " headings
    sections = []  # list of (section_title, body_lines)
    current_title = None
    current_body = []
    for line in lines:
        if line.startswith("# ") and current_title is None and not sections:
            continue  # skip the doc title line
        if line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, current_body))
            current_title = line[3:].strip()
            current_body = []
        else:
            if current_title is not None:
                current_body.append(line)

    if current_title is not None:
        sections.append((current_title, current_body))

    # build chunks, splitting any oversized section by paragraphs
    chunks = []
    for section_title, body_lines in sections:
        body = "\n".join(body_lines).strip()
        if not body:
            continue
        for piece in _split_if_long(body):
            content = f"{doc_title} — {section_title}\n\n{piece}"
            chunks.append((section_title, doc_title, content))
    return chunks


def _split_if_long(body):
    """Split a long body into <= MAX_CHARS pieces on paragraph boundaries."""
    if len(body) <= MAX_CHARS:
        return [body]
    paragraphs = re.split(r"\n\s*\n", body)
    pieces, buf = [], ""
    for p in paragraphs:
        if buf and len(buf) + len(p) + 2 > MAX_CHARS:
            pieces.append(buf.strip())
            buf = p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


# ---------------------------------------------------------------------------
# 2. Persist
# ---------------------------------------------------------------------------
def ingest_document(conn, path):
    source = path.name
    chunks = chunk_markdown(path.read_text())

    with conn.cursor() as cur:
        # clean slate for this document, then insert fresh chunks
        cur.execute("DELETE FROM document_chunks WHERE source = %s", (source,))
        for idx, (section_title, doc_title, content) in enumerate(chunks):
            vector = embed(content)
            metadata = {"doc_title": doc_title, "section": section_title}
            cur.execute(
                """
                INSERT INTO document_chunks
                    (source, doc_type, chunk_index, content, embedding, metadata)
                VALUES (%s, 'policy', %s, %s, %s, %s)
                """,
                (source, idx, content, vector, json.dumps(metadata)),
            )
    return len(chunks)


def main():
    load_dotenv(REPO_ROOT / "backend" / ".env")
    url = os.environ["DATABASE_URL"]

    files = sorted(POLICIES_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"No markdown files found in {POLICIES_DIR}")

    with psycopg.connect(url) as conn:
        register_vector(conn)
        total = 0
        for path in files:
            n = ingest_document(conn, path)
            total += n
            print(f"  {path.name}: {n} chunks")
        conn.commit()

    print(f"Ingestion complete: {len(files)} documents, {total} chunks embedded.")


if __name__ == "__main__":
    main()
