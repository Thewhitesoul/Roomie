"""Extra FR-01 tests so every path of auth.register() is exercised.

Milestone 7 cyclomatic-complexity analysis: see docs/testing-plan.md, section 9.
Uses the temporary-database fixtures from conftest.py and fictional data only.
"""
import sqlite3

from app import auth as auth_module
from app.db import get_db


def post_register(client, **overrides):
    body = {"username": "arpan", "email": "arpan@washburn.edu", "password": "password123"}
    body.update(overrides)
    return client.post("/auth/register", json=body)


def user_count(app):
    with app.app_context():
        return get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0]


# TC-M7-03: username one character below the 3-character minimum
def test_register_username_too_short(client, app):
    resp = post_register(client, username="ab")
    assert resp.status_code == 400
    assert user_count(app) == 0


# TC-M7-07: password exactly at the 8-character minimum is accepted
def test_register_password_exactly_minimum(client, app):
    resp = post_register(client, password="a" * 8)
    assert resp.status_code == 201
    assert user_count(app) == 1


# TC-M7-13: a non-text value is rejected by text_field(), not crashed on
def test_register_non_text_field_rejected(client, app):
    resp = client.post("/auth/register", json={
        "username": "arpan", "email": 123, "password": "password123",
    })
    assert resp.status_code == 400
    assert "text" in resp.get_json()["error"]
    assert user_count(app) == 0


# TC-M7-14: if the INSERT hits a uniqueness error (two sign-ups racing),
# the user gets a 409 and no row is stored. The existence checks are real;
# only the INSERT is forced to fail.
def test_register_insert_integrity_error_returns_409(client, app, monkeypatch):
    real_get_db = auth_module.get_db

    class FailingInsert:
        def __init__(self, real):
            self._real = real

        def execute(self, sql, *args):
            if sql.lstrip().upper().startswith("INSERT INTO USERS"):
                raise sqlite3.IntegrityError("simulated race")
            return self._real.execute(sql, *args)

        def __getattr__(self, name):
            return getattr(self._real, name)

    monkeypatch.setattr(auth_module, "get_db", lambda: FailingInsert(real_get_db()))

    resp = post_register(client)

    assert resp.status_code == 409
    assert "taken" in resp.get_json()["error"]
    assert user_count(app) == 0
