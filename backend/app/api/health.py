import psycopg
from flask import Blueprint, current_app, jsonify

bp = Blueprint("health", __name__)

@bp.get("/health")
def health():
    try:
        with psycopg.connect(current_app.config["DATABASE_URL"], connect_timeout=2) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return jsonify(status="ok", db="up"), 200
    except Exception as e:
        return jsonify(status="degraded", db="down", error=str(e)), 503
