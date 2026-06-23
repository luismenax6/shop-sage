"""Agent tools: catalog search (read) and the action implementations.

Each tool has two parts:
  - a *spec* (name + description + JSON input schema) that we hand to Claude so
    it knows when and how to call the tool;
  - a Python *implementation* that runs the real work against Postgres.

`TOOL_SPECS` is the Bedrock Converse `toolConfig` payload; `dispatch()` routes a
tool-use request from Claude to the matching implementation.
"""

import uuid

from psycopg.rows import dict_row

from app.rag.retrieval import retrieve_with_guardrail

# ---------------------------------------------------------------------------
# Implementations
# ---------------------------------------------------------------------------
def search_products(
    conn,
    category=None,
    min_price=None,
    max_price=None,
    in_stock_only=True,
    keywords=None,
    limit=5,
):
    """Search the catalog. Returns a list of product dicts."""
    conditions, params = [], []
    if category:
        conditions.append("category ILIKE %s")
        params.append(f"%{category}%")
    if min_price is not None:
        conditions.append("price >= %s")
        params.append(min_price)
    if max_price is not None:
        conditions.append("price <= %s")
        params.append(max_price)
    if in_stock_only:
        conditions.append("stock > 0")
    if keywords:
        conditions.append("(name ILIKE %s OR description ILIKE %s)")
        params.extend([f"%{keywords}%", f"%{keywords}%"])

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = (
        f"SELECT sku, name, category, price, stock, description "
        f"FROM products {where} ORDER BY price LIMIT %s"
    )
    params.append(limit)

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(sql, params)
        rows = cur.fetchall()

    for r in rows:
        r["price"] = float(r["price"])  # Decimal -> float for JSON
    return rows


def add_to_cart(conn, user_id, sku, quantity=1):
    """Add a product to the user's cart (idempotent upsert). WRITE."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("SELECT id, name, price FROM products WHERE sku = %s", (sku,))
        product = cur.fetchone()
        if product is None:
            return {"status": "error", "message": f"No product found with sku {sku}"}

        # Idempotent: the UNIQUE(user_id, product_id) constraint turns a repeat
        # add into an update, so retrying the same request never duplicates.
        cur.execute(
            """
            INSERT INTO cart_items (user_id, product_id, quantity)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, product_id)
            DO UPDATE SET quantity = EXCLUDED.quantity, added_at = now()
            """,
            (user_id, product["id"], quantity),
        )
        cur.execute(
            """
            SELECT COALESCE(SUM(p.price * c.quantity), 0) AS total,
                   COALESCE(SUM(c.quantity), 0) AS items
            FROM cart_items c JOIN products p ON p.id = c.product_id
            WHERE c.user_id = %s
            """,
            (user_id,),
        )
        cart = cur.fetchone()
    conn.commit()
    return {
        "status": "added",
        "sku": sku,
        "name": product["name"],
        "quantity": quantity,
        "cart_items": int(cart["items"]),
        "cart_total": float(cart["total"]),
    }


def create_ticket(conn, user_id, subject, body, related_order=None):
    """Open a support ticket to escalate to a human (idempotent). WRITE."""
    with conn.cursor(row_factory=dict_row) as cur:
        # Idempotent: if an identical open ticket already exists, reuse it
        # instead of opening a duplicate.
        cur.execute(
            """
            SELECT ticket_number FROM tickets
            WHERE user_id = %s AND subject = %s AND body = %s AND status = 'open'
            """,
            (user_id, subject, body),
        )
        existing = cur.fetchone()
        if existing:
            return {"status": "exists", "ticket_number": existing["ticket_number"]}

        ticket_number = "TK-" + uuid.uuid4().hex[:8].upper()
        cur.execute(
            """
            INSERT INTO tickets (ticket_number, user_id, subject, body, related_order)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (ticket_number, user_id, subject, body, related_order),
        )
    conn.commit()
    return {"status": "created", "ticket_number": ticket_number}


def search_documentation(conn, question):
    """Look up support/policy documents via RAG. Returns chunks with citations."""
    hits = retrieve_with_guardrail(conn, question)
    if hits is None:
        return {"status": "no_relevant_docs"}
    return {
        "status": "ok",
        "chunks": [
            {
                "content": h["content"],
                "source": h["source"],
                "section": h["section"],
                "similarity": round(h["similarity"], 3),
            }
            for h in hits
        ],
    }


# ---------------------------------------------------------------------------
# Tool specs handed to Claude (Bedrock Converse toolConfig)
# ---------------------------------------------------------------------------
TOOL_SPECS = {
    "tools": [
        {
            "toolSpec": {
                "name": "search_products",
                "description": (
                    "Search the product catalog to recommend gifts. Filter by "
                    "category, price range, stock, and free-text keywords. Use "
                    "this whenever the shopper is looking for a product."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "category": {
                                "type": "string",
                                "description": "Category to match, e.g. 'Camping', 'Grilling', 'Tech'.",
                            },
                            "min_price": {"type": "number", "description": "Minimum price in USD."},
                            "max_price": {"type": "number", "description": "Maximum price (budget) in USD."},
                            "in_stock_only": {
                                "type": "boolean",
                                "description": "Only return products currently in stock. Default true.",
                            },
                            "keywords": {
                                "type": "string",
                                "description": "Free text matched against product name and description.",
                            },
                        },
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "add_to_cart",
                "description": (
                    "Add a product to the shopper's cart. This changes their cart, "
                    "so only call it after the shopper has confirmed they want the item."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "sku": {"type": "string", "description": "The product SKU, e.g. 'CAMP-003'."},
                            "quantity": {"type": "integer", "description": "How many to add. Default 1."},
                        },
                        "required": ["sku"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "create_ticket",
                "description": (
                    "Open a support ticket to escalate the shopper to a human agent. "
                    "Use when you cannot resolve their issue. Confirm with the shopper first."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "subject": {"type": "string", "description": "Short summary of the issue."},
                            "body": {"type": "string", "description": "Full description of the issue."},
                            "related_order": {"type": "string", "description": "Order number if relevant, e.g. 'SS-10003'."},
                        },
                        "required": ["subject", "body"],
                    }
                },
            }
        },
        {
            "toolSpec": {
                "name": "search_documentation",
                "description": (
                    "Look up store policies and FAQs (shipping, returns, warranty, "
                    "payment, gifts) to answer support questions. Use this for any "
                    "question about policies. Base your answer only on the returned "
                    "text and cite the source document."
                ),
                "inputSchema": {
                    "json": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "The support question to look up in the docs.",
                            },
                        },
                        "required": ["question"],
                    }
                },
            }
        },
    ]
}

# ---------------------------------------------------------------------------
# Dispatch: route a tool name from Claude to its implementation
# ---------------------------------------------------------------------------
_IMPLEMENTATIONS = {
    "search_products": search_products,
    "add_to_cart": add_to_cart,
    "create_ticket": create_ticket,
    "search_documentation": search_documentation,
}

READ_TOOLS = {"search_products", "search_documentation"}
WRITE_TOOLS = {"add_to_cart", "create_ticket"}


def dispatch(conn, tool_name, tool_input):
    impl = _IMPLEMENTATIONS.get(tool_name)
    if impl is None:
        raise ValueError(f"unknown tool: {tool_name}")
    return impl(conn, **tool_input)
