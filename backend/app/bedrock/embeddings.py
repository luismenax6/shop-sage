"""Shared embedding client (AWS Bedrock, Amazon Titan Text v2).

Single source of truth for turning text into a 1024-dim vector. Used by both
the ingestion script and the RAG retrieval layer so the query and the stored
chunks always live in the same vector space.
"""

import json

import boto3

EMBED_MODEL_ID = "amazon.titan-embed-text-v2:0"  # 1024 dims, no inference profile needed
REGION = "us-east-1"

_bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def embed(text):
    """Return the 1024-float embedding for a piece of text."""
    resp = _bedrock.invoke_model(
        modelId=EMBED_MODEL_ID,
        body=json.dumps({"inputText": text}),
    )
    return json.loads(resp["body"].read())["embedding"]
