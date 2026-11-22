import pytest
from flask.testing import FlaskClient

from app import create_app
from app.db import get_db, init_db


class CSRFClient(FlaskClient):
    """Exercise real token validation for ordinary API tests, without disabling it."""
    def open(self, *args, **kwargs):
        if kwargs.get("method", "GET").upper() not in {"GET", "HEAD", "OPTIONS"}:
            token = self.get("/auth/csrf").get_json()["csrf_token"]
            kwargs.setdefault("headers", {}).setdefault("X-CSRF-Token", token)
        return super().open(*args, **kwargs)

@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path/"test.sqlite"),
        "SECRET_KEY":"test",
    })
    with app.app_context():
        init_db()
    yield app

@pytest.fixture
def client(app):
    app.test_client_class = CSRFClient
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()
