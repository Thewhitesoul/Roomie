import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.db import get_db


@pytest.fixture
def owner(app, client):
    with app.app_context():
        db = get_db()
        for name in ("owner", "other"):
            db.execute(
                "INSERT INTO users "
                "(username, email, password_hash) VALUES (?, ?, ?)",
                (
                    name,
                    name + "@example.com",
                    generate_password_hash(
                        "password123", method="pbkdf2:sha256"
                    ),
                ),
            )
        db.commit()

    with client.session_transaction() as session:
        session["user_id"] = 1

    return client


def test_authentication(client):
    assert client.get("/preferences/me").status_code == 401
    assert client.put("/preferences/me", json={}).status_code == 401


def test_fields(owner):
    data = {
        "cleanliness": "tidy",
        "sleep_schedule": "early",
        "study_habits": "quiet",
        "smoking_preference": "no",
        "pet_preference": "yes",
        "budget": 600,
    }

    assert owner.get("/preferences/me").json["budget"] is None

    response = owner.put("/preferences/me", json=data)
    assert response.status_code == 200
    assert response.json == {"user_id": 1, **data}

    response = owner.put("/preferences/me", json={"budget": 700})
    assert response.json["cleanliness"] == "tidy"

    response = owner.put("/preferences/me", json={"budget": None})
    assert response.json["budget"] is None


@pytest.mark.parametrize(
    "budget",
    [-1, 2.5, 600.0, True, "600", [], 2**63],
)
def test_invalid_budget(owner, budget):
    response = owner.put("/preferences/me", json={"budget": budget})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "data",
    [
        [],
        None,
        {"user_id": 2},
        {"id": 2},
        {"unknown": "x"},
        {"cleanliness": ""},
        {"sleep_schedule": False},
        {"study_habits": []},
        {"smoking_preference": "x" * 101},
        {"pet_preference": "a\nb"},
    ],
)
def test_invalid_input(owner, data):
    assert owner.put("/preferences/me", json=data).status_code == 400


def test_isolation(owner):
    owner.put("/preferences/me", json={"budget": 600})

    response = owner.put(
        "/preferences/me", json={"user_id": 2, "budget": 900}
    )
    assert response.status_code == 400
    assert owner.put(
        "/preferences/2", json={"budget": 900}
    ).status_code == 404

    with owner.session_transaction() as session:
        session["user_id"] = 2

    assert owner.get("/preferences/me").json["budget"] is None
    owner.put("/preferences/me", json={"budget": 800})

    with owner.session_transaction() as session:
        session["user_id"] = 1

    assert owner.get("/preferences/me").json["budget"] == 600


def test_persistence(app, owner):
    owner.put(
        "/preferences/me",
        json={"budget": 600, "cleanliness": "tidy"},
    )
    assert owner.post("/auth/logout", json={}).status_code == 200
    assert owner.get("/preferences/me").status_code == 401

    credentials = {
        "email": "owner@example.com",
        "password": "password123",
    }
    assert owner.post(
        "/auth/login", json=credentials
    ).status_code == 200
    assert owner.get("/preferences/me").json["budget"] == 600

    for _ in range(2):
        result = app.test_cli_runner().invoke(args=["init-db"])
        assert result.exit_code == 0, result.output

    restarted = create_app(dict(app.config, TESTING=True))
    client = restarted.test_client()

    assert client.post(
        "/auth/login", json=credentials,
        headers={"X-CSRF-Token": client.get('/auth/csrf').json['csrf_token']},
    ).status_code == 200

    saved = client.get("/preferences/me").json
    assert saved["budget"] == 600
    assert saved["cleanliness"] == "tidy"
