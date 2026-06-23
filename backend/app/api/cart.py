"""Cart endpoints for deterministic UI actions.

Clicking "add to cart" on a product card is an explicit, unambiguous mutation,
so it goes straight to the cart logic instead of through the conversational
agent. Both paths reuse the same idempotent add_to_cart implementation.
"""

import psycopg
from flask import Blueprint, current_app, jsonify, request

from app.agent.tools import add_to_cart, get_cart

bp = Blueprint("cart", __name__)


@bp.get("/cart")
def view_cart():
    user_id = request.args.get("user_id", "user_demo")
    with psycopg.connect(current_app.config["DATABASE_URL"]) as conn:
        cart = get_cart(conn, user_id)
    return jsonify(cart)


@bp.post("/cart/add")
def add_item():
    data = request.get_json(silent=True) or {}
    sku = data.get("sku")
    if not sku:
        return jsonify(error="'sku' is required"), 400
    quantity = int(data.get("quantity", 1))
    user_id = data.get("user_id", "user_demo")

    with psycopg.connect(current_app.config["DATABASE_URL"]) as conn:
        result = add_to_cart(conn, user_id, sku, quantity)
        if result.get("status") == "error":
            return jsonify(error=result["message"]), 404
        cart = get_cart(conn, user_id)
    return jsonify(cart)
