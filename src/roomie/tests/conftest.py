import pytest

from app import create_app
from app.db import get_db, init_db

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
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def db(app):
    with app.app_context():
        yield get_db()