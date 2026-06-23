"""Shared text-generation client (AWS Bedrock, Claude via Converse API).

Claude models are invoked through an inference profile (the `us.` prefix); the
bare on-demand model id raises ValidationException.
"""

import boto3

GEN_MODEL_ID = "us.anthropic.claude-sonnet-4-6"  # inference profile, not bare id
REGION = "us-east-1"

_bedrock = boto3.client("bedrock-runtime", region_name=REGION)


def generate(system_prompt, user_message, max_tokens=500, temperature=0.2):
    """Single-turn generation. Returns Claude's reply text."""
    resp = _bedrock.converse(
        modelId=GEN_MODEL_ID,
        system=[{"text": system_prompt}],
        messages=[{"role": "user", "content": [{"text": user_message}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
    )
    return resp["output"]["message"]["content"][0]["text"]
