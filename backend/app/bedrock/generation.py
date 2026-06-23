"""Shared Bedrock generation client (Claude via the Converse API).

Claude is invoked through an inference profile (the `us.` prefix); the bare
on-demand model id raises ValidationException. The agent orchestrator uses this
client and model id so there's a single source of truth for generation config.
"""

import boto3

GEN_MODEL_ID = "us.anthropic.claude-sonnet-4-6"  # inference profile, not bare id
REGION = "us-east-1"

client = boto3.client("bedrock-runtime", region_name=REGION)
