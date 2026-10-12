import pytest

from app import create_app


@pytest.fixture
def app(tmp_path):
    config = {
        "TESTING": True,
        "DATA_DIR": str(tmp_path),
    }

    app = create_app(config)
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()