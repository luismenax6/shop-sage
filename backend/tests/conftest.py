"""Shared pytest fixtures.

DB-backed tests use the local dev database (docker compose up + seeded). They
read against the seeded data and isolate writes under a dedicated test user
that is cleaned up before and after each test.
"""

import os

import psycopg
import pytest
from dotenv import load_dotenv
from pgvector.psycopg import register_vector

TEST_USER = "pytest_user"


@pytest.fixture
def db():
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    conn = psycopg.connect(os.environ["DATABASE_URL"])
    register_vector(conn)
    yield conn
    conn.close()


@pytest.fixture
def test_user(db):
    """A clean, isolated user id for write tests."""
    def _clean():
        with db.cursor() as cur:
            cur.execute("DELETE FROM cart_items WHERE user_id = %s", (TEST_USER,))
            cur.execute("DELETE FROM tickets WHERE user_id = %s", (TEST_USER,))
        db.commit()

    _clean()
    yield TEST_USER
    _clean()
