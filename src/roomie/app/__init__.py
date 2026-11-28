import os
import secrets
from pathlib import Path
from flask import Flask
from werkzeug.routing import IntegerConverter
from .profile import profiles_bp
from . import db, security
from . import auth
from . import profile
from .matches import matches_bp
from .interests import interest_bp
from .preferences import preferences_bp
from .frontend import register_pages
from . import seed


class SQLiteIDConverter(IntegerConverter):
    """Every integer URL parameter in this app addresses a SQLite ID."""
    # Bound length before int() runs. Views check the SQLite range so invalid
    # IDs retain their existing authenticated JSON/HTML 404 responses.
    regex = r"\d{1,19}"


def create_app(test_config=None):
    frontend_root = Path(__file__).resolve().parents[2]
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder=str(frontend_root / "templates"),
        static_folder=str(frontend_root / "static"),
    )
    app.url_map.converters['int'] = SQLiteIDConverter

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("ROOMIE_COOKIE_SECURE", "1") != "0",
        DATABASE=os.path.join(app.instance_path, "roomie.sqlite"),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    security.init_app(app)
    db.init_app(app)
    seed.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(profiles_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(interest_bp)
    app.register_blueprint(preferences_bp)
    register_pages(app)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
