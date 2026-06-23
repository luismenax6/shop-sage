"""Seed the database with synthetic catalog and order data.

Idempotent: re-running upserts products and skips existing orders, so it is
safe to run multiple times. Embeddings are NOT handled here — that belongs to
the ingestion script (RAG step).

Usage:
    cd backend && source .venv/bin/activate
    python scripts/seed_data.py
"""

import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"


def load_products(conn):
    products = json.loads((DATA_DIR / "products.json").read_text())
    with conn.cursor() as cur:
        for p in products:
            cur.execute(
                """
                INSERT INTO products (sku, name, category, price, stock, description, image_url)
                VALUES (%(sku)s, %(name)s, %(category)s, %(price)s, %(stock)s,
                        %(description)s, %(image_url)s)
                ON CONFLICT (sku) DO UPDATE SET
                    name        = EXCLUDED.name,
                    category    = EXCLUDED.category,
                    price       = EXCLUDED.price,
                    stock       = EXCLUDED.stock,
                    description = EXCLUDED.description,
                    image_url   = EXCLUDED.image_url
                """,
                p,
            )
    return len(products)


def load_orders(conn):
    orders = json.loads((DATA_DIR / "orders.json").read_text())
    inserted = 0
    with conn.cursor() as cur:
        for o in orders:
            # skip if the order already exists (idempotent)
            cur.execute(
                "SELECT id FROM orders WHERE order_number = %s", (o["order_number"],)
            )
            if cur.fetchone():
                continue

            # resolve products and compute totals
            line_items = []
            total = 0
            for item in o["items"]:
                cur.execute(
                    "SELECT id, price FROM products WHERE sku = %s", (item["sku"],)
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(f"order {o['order_number']} references unknown sku {item['sku']}")
                product_id, price = row
                line_items.append((product_id, item["quantity"], price))
                total += price * item["quantity"]

            cur.execute(
                """
                INSERT INTO orders (order_number, user_id, status, total)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (o["order_number"], o["user_id"], o["status"], total),
            )
            order_id = cur.fetchone()[0]

            for product_id, quantity, unit_price in line_items:
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (order_id, product_id, quantity, unit_price),
                )
            inserted += 1
    return inserted


def main():
    load_dotenv(REPO_ROOT / "backend" / ".env")
    url = os.environ["DATABASE_URL"]
    with psycopg.connect(url) as conn:
        n_products = load_products(conn)
        n_orders = load_orders(conn)
        conn.commit()
    print(f"Seed complete: {n_products} products upserted, {n_orders} new orders inserted.")


if __name__ == "__main__":
    main()
