"""Write tools are idempotent: retrying never duplicates."""

from app.agent.tools import add_to_cart, create_ticket


def test_add_to_cart_is_idempotent(db, test_user):
    add_to_cart(db, test_user, "CAMP-003", 1)
    add_to_cart(db, test_user, "CAMP-003", 1)  # retry

    with db.cursor() as cur:
        cur.execute(
            "SELECT count(*), max(quantity) FROM cart_items WHERE user_id = %s",
            (test_user,),
        )
        count, quantity = cur.fetchone()
    assert count == 1  # one row, not two
    assert quantity == 1


def test_add_to_cart_unknown_sku_errors(db, test_user):
    result = add_to_cart(db, test_user, "NOPE-999", 1)
    assert result["status"] == "error"


def test_create_ticket_is_idempotent(db, test_user):
    first = create_ticket(db, test_user, "Damaged item", "It arrived broken")
    second = create_ticket(db, test_user, "Damaged item", "It arrived broken")

    assert first["status"] == "created"
    assert second["status"] == "exists"
    assert first["ticket_number"] == second["ticket_number"]
