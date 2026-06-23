"""search_products applies catalog filters correctly (read-only, seeded DB)."""

from app.agent.tools import search_products


def test_filters_by_category_and_max_price(db):
    rows = search_products(db, category="Camping", max_price=100)
    assert rows  # there are camping items under $100
    assert all(r["price"] <= 100 for r in rows)
    assert all("Camping" in r["category"] for r in rows)


def test_in_stock_only_excludes_zero_stock(db):
    rows = search_products(db, in_stock_only=True, limit=100)
    assert all(r["stock"] > 0 for r in rows)


def test_out_of_stock_included_when_disabled(db):
    rows = search_products(db, in_stock_only=False, limit=100)
    assert any(r["stock"] == 0 for r in rows)  # dataset has out-of-stock items


def test_keywords_match_description(db):
    rows = search_products(db, keywords="whiskey", in_stock_only=False)
    assert any("whiskey" in (r["name"] + r["description"]).lower() for r in rows)
