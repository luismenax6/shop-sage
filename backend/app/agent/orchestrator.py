"""Agent orchestration: the Bedrock Converse tool-calling loop.

Claude is given the user's message plus the tool specs. It may answer directly,
or ask to call a tool. We run read tools immediately; write tools are gated
behind explicit user confirmation (`confirm=True`) so the agent never changes
state on its own. Identity (`user_id`) is injected by the server, never chosen
by the model.

The conversation `messages` list is returned so a multi-turn chat (e.g. ask ->
user confirms -> execute) can continue across calls.
"""

import boto3

from app.agent.tools import TOOL_SPECS, WRITE_TOOLS, dispatch

GEN_MODEL_ID = "us.anthropic.claude-sonnet-4-6"
REGION = "us-east-1"
_bedrock = boto3.client("bedrock-runtime", region_name=REGION)

SYSTEM_PROMPT = (
    "You are ShopSage, a friendly shopping assistant for a gift store. "
    "When a shopper looks for a product, call search_products to find real items "
    "— never invent products, and only recommend items the tool returned. The UI "
    "already shows the results as cards (image, price, stock, Add button), so keep "
    "your reply short and conversational: highlight one or two picks in a sentence "
    "or two and do NOT list every product or repeat prices in a table. "
    "For questions about policies (shipping, returns, warranty, payment, gifts), "
    "call search_documentation and answer ONLY from the returned text, citing the "
    "source document; if it returns no relevant docs, say you don't have that "
    "information and offer to open a support ticket. "
    "Before adding anything to the cart or opening a support ticket, confirm the "
    "details with the shopper first. If a write tool reports it needs "
    "confirmation, ask the shopper to confirm and try again once they say yes. "
    "Keep replies concise and helpful."
)


def _text_of(message):
    return "".join(b["text"] for b in message["content"] if "text" in b)


def run_agent(conn, user_message, history=None, user_id="user_demo", confirm=False, max_turns=5):
    """Run the tool-calling loop. Returns {answer, tool_calls, messages}."""
    messages = list(history or [])
    messages.append({"role": "user", "content": [{"text": user_message}]})
    tool_calls = []

    for _ in range(max_turns):
        resp = _bedrock.converse(
            modelId=GEN_MODEL_ID,
            system=[{"text": SYSTEM_PROMPT}],
            messages=messages,
            toolConfig=TOOL_SPECS,
            inferenceConfig={"maxTokens": 800, "temperature": 0.3},
        )
        assistant_msg = resp["output"]["message"]
        messages.append(assistant_msg)

        if resp["stopReason"] != "tool_use":
            return {"answer": _text_of(assistant_msg), "tool_calls": tool_calls, "messages": messages}

        tool_result_blocks = []
        for block in assistant_msg["content"]:
            if "toolUse" not in block:
                continue
            tu = block["toolUse"]
            name, tool_input = tu["name"], tu["input"]

            if name in WRITE_TOOLS and not confirm:
                # gate: do not mutate state until the user confirms
                result = {"status": "confirmation_required", "action": name, "details": tool_input}
                tool_calls.append({"name": name, "input": tool_input, "status": "awaiting_confirmation"})
            else:
                if name in WRITE_TOOLS:
                    tool_input = {**tool_input, "user_id": user_id}  # server-supplied identity
                result = dispatch(conn, name, tool_input)
                tool_calls.append({"name": name, "input": tu["input"], "status": "executed", "result": result})

            tool_result_blocks.append(
                {"toolResult": {"toolUseId": tu["toolUseId"], "content": [{"json": {"result": result}}]}}
            )
        messages.append({"role": "user", "content": tool_result_blocks})

    return {"answer": "(stopped: too many tool turns)", "tool_calls": tool_calls, "messages": messages}
