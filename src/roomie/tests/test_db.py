import sqlite3

import pytest

from app import create_app
from app.db import get_db, init_db


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() == {"status": "ok"}


def test_tables_exist(db):
    names = {r["name"] for r in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"users", "profiles", "profile_interests", "connection_requests"} <= names


def test_same_connection_within_request(app):
    with app.app_context():
        assert get_db() is get_db()


def test_connection_closed_after_request(app):
    with app.app_context():
        db = get_db()
    with pytest.raises(sqlite3.ProgrammingError):
        db.execute("SELECT 1")


def test_init_db_command(runner):
    result = runner.invoke(args=["init-db"])
    assert "Initialized" in result.output


def test_data_survives_restart(tmp_path):
    config = {"TESTING": True, "DATABASE": str(tmp_path / "keep.sqlite")}
    app = create_app(config)
    with app.app_context():
        init_db()
        get_db().execute("INSERT INTO users (username, email, password_hash) VALUES ('a', 'a@x.edu', 'h')")
        get_db().commit()

    restarted = create_app(config)
    with restarted.app_context():
        assert get_db().execute("SELECT COUNT(*) FROM users").fetchone()[0] == 1


# ---------- rules the database enforces on its own ----------

def _user(db, name):
    return db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, 'h')",
        (name, f"{name}@x.edu"),
    ).lastrowid


def test_foreign_keys_enforced(db):
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO profiles (user_id, name) VALUES (999, 'Ghost')")


def test_no_negative_budget(db):
    uid = _user(db, "a")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO profiles (user_id, name, budget) VALUES (?, 'A', -1)", (uid,))


def test_no_connection_request_to_self(db):
    uid = _user(db, "a")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO connection_requests (from_user_id, to_user_id) VALUES (?, ?)", (uid, uid))


def test_no_duplicate_connection_request(db):
    a, b = _user(db, "a"), _user(db, "b")
    db.execute("INSERT INTO connection_requests (from_user_id, to_user_id) VALUES (?, ?)", (a, b))
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("INSERT INTO connection_requests (from_user_id, to_user_id) VALUES (?, ?)", (a, b))


def test_deleting_user_removes_their_data(db):
    a, b = _user(db, "a"), _user(db, "b")
    pid = db.execute("INSERT INTO profiles (user_id, name) VALUES (?, 'A')", (a,)).lastrowid
    db.execute("INSERT INTO profile_interests (profile_id, interest) VALUES (?, 'gaming')", (pid,))
    db.execute("INSERT INTO connection_requests (from_user_id, to_user_id) VALUES (?, ?)", (a, b))

    db.execute("DELETE FROM users WHERE id = ?", (a,))

    for table in ("profiles", "profile_interests", "connection_requests"):
        assert db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0