"""One-off database bootstrap for a deployed environment.

Applies the schema, loads the synthetic catalog/orders, and ingests the policy
documents (embeddings) in one shot. Designed to run as a one-off ECS task inside
the VPC, so it can reach the private RDS instance without exposing it:

    aws ecs run-task ... --overrides '{"containerOverrides":[{"name":"backend",
      "command":["python","scripts/bootstrap_db.py"]}]}'

Reads DATABASE_URL from the environment (injected from Secrets Manager). Safe to
re-run: the schema uses IF NOT EXISTS and the seed/ingest are idempotent.
"""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))  # so `import app...` works (used by ingest)

import psycopg  # noqa: E402

import ingest  # noqa: E402
import seed_data  # noqa: E402


def apply_schema(url):
    schema_sql = (BACKEND / "db" / "schema.sql").read_text()
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute(schema_sql)  # DDL only, no params -> multi-statement is fine
    print("schema applied")


def main():
    url = os.environ["DATABASE_URL"]
    apply_schema(url)
    seed_data.main()  # products + orders
    ingest.main()     # policy documents -> embeddings -> pgvector
    print("bootstrap complete")


if __name__ == "__main__":
    main()
