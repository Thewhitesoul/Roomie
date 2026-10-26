import os
from flask import Flask
from .profile import profiles_bp
from . import db
from . import auth
from . import profile

def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
        DATA_DIR=os.path.join(app.instance_path),
    )

    if test_config is None:
        app.config.from_pyfile("config.py", silent=True)
    else:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(profiles_bp)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
