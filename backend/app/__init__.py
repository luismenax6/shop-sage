import os
from flask import Flask
from dotenv import load_dotenv

def create_app():
    load_dotenv()
    app = Flask(__name__)
    app.config["DATABASE_URL"] = os.environ["DATABASE_URL"]

    from app.api.health import bp as health_bp
    app.register_blueprint(health_bp)

    from app.api.chat import bp as chat_bp
    app.register_blueprint(chat_bp)

    return app