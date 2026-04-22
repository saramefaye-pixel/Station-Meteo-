from flask import Flask
from flask_session import Session
import os

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # ── Configuration de la session ──────────────────────────────────────────
    app.config["SECRET_KEY"] = "agroTIC-station-meteo-2025-sfisenegall"
    app.config["SESSION_TYPE"] = "filesystem"
    app.config["SESSION_FILE_DIR"] = os.path.join(os.path.dirname(__file__), "../.flask_sessions")
    app.config["SESSION_PERMANENT"] = False
    os.makedirs(app.config["SESSION_FILE_DIR"], exist_ok=True)
    Session(app)

    from app.routes import bp
    app.register_blueprint(bp)

    return app
