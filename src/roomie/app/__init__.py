import os
from flask import Flask


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
    
    from . import storage

    with app.app_context():
        storage.initialize_storage()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app