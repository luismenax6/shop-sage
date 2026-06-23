"""Ingestion worker: S3 document -> chunks -> Titan embeddings -> pgvector.

Triggered by SQS (fed by S3 ObjectCreated events). Mirrors the chunking and
embedding logic of backend/scripts/ingest.py, but as a serverless worker — no C
extension is needed here (that's only for retrieval), so it runs fine on Lambda.

Requires a layer providing psycopg + pgvector; boto3 is in the Lambda runtime.
"""

import json
import os
import re
import urllib.parse

import boto3
import psycopg
from pgvector.psycopg import register_vector

EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"  # 1024 dims
REGION = os.environ.get("AWS_REGION", "us-east-1")
MAX_CHARS = 1500

s3 = boto3.client("s3")
bedrock = boto3.client("bedrock-runtime", region_name=REGION)
secrets = boto3.client("secretsmanager")

_db_url = None


def _database_url():
    global _db_url
    if _db_url is None:
        _db_url = secrets.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"]
    return _db_url


def embed(text):
    resp = bedrock.invoke_model(modelId=EMBED_MODEL_ID, body=json.dumps({"inputText": text}))
    return json.loads(resp["body"].read())["embedding"]


def chunk_markdown(text):
    """Split a markdown doc into (section, doc_title, content) chunks."""
    lines = text.splitlines()
    doc_title = lines[0][2:].strip() if lines and lines[0].startswith("# ") else "Untitled"

    sections, title, body = [], None, []
    for line in lines:
        if line.startswith("# ") and title is None and not sections:
            continue
        if line.startswith("## "):
            if title is not None:
                sections.append((title, body))
            title, body = line[3:].strip(), []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections.append((title, body))

    chunks = []
    for section, body_lines in sections:
        text_body = "\n".join(body_lines).strip()
        if not text_body:
            continue
        for piece in _split_if_long(text_body):
            chunks.append((section, doc_title, f"{doc_title} — {section}\n\n{piece}"))
    return chunks


def _split_if_long(body):
    if len(body) <= MAX_CHARS:
        return [body]
    pieces, buf = [], ""
    for p in re.split(r"\n\s*\n", body):
        if buf and len(buf) + len(p) + 2 > MAX_CHARS:
            pieces.append(buf.strip())
            buf = p
        else:
            buf = f"{buf}\n\n{p}" if buf else p
    if buf.strip():
        pieces.append(buf.strip())
    return pieces


def _ingest_object(conn, bucket, key):
    text = s3.get_object(Bucket=bucket, Key=key)["Body"].read().decode("utf-8")
    source = key.split("/")[-1]
    chunks = chunk_markdown(text)
    with conn.cursor() as cur:
        cur.execute("DELETE FROM document_chunks WHERE source = %s", (source,))
        for idx, (section, doc_title, content) in enumerate(chunks):
            cur.execute(
                """
                INSERT INTO document_chunks
                    (source, doc_type, chunk_index, content, embedding, metadata)
                VALUES (%s, 'policy', %s, %s, %s, %s)
                """,
                (source, idx, content, embed(content),
                 json.dumps({"doc_title": doc_title, "section": section})),
            )
    conn.commit()
    print(f"ingested {source}: {len(chunks)} chunks")


def handler(event, context):
    with psycopg.connect(_database_url()) as conn:
        register_vector(conn)
        for record in event["Records"]:               # SQS records
            body = json.loads(record["body"])          # S3 event
            for s3rec in body.get("Records", []):
                bucket = s3rec["s3"]["bucket"]["name"]
                key = urllib.parse.unquote_plus(s3rec["s3"]["object"]["key"])
                _ingest_object(conn, bucket, key)
    return {"status": "ok"}
