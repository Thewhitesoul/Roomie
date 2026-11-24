"""Fake demo data from `flask --app app seed`."""
from app.db import get_db
from app.frontend import PREFERENCE_FIELDS
from app.profile_state import is_complete
from app.seed import FAKE_DOMAIN, seed_fake_data


def count(app, sql, *args):
    with app.app_context():
        return get_db().execute(sql, args).fetchone()[0]


def fake_users(app):
    return count(app, "SELECT COUNT(*) FROM users WHERE email LIKE ?", f"%@{FAKE_DOMAIN}")


def test_seed_command_adds_100_users(app, runner):
    result = runner.invoke(args=["seed"])
    assert result.exit_code == 0, result.output
    assert "Added 100 fake users" in result.output
    assert fake_users(app) == 100


def test_every_fake_user_has_a_complete_profile_interests_and_preferences(app):
    with app.app_context():
        seed_fake_data(100)
        db = get_db()
        profiles = db.execute("SELECT * FROM profiles").fetchall()
        assert len(profiles) == 100
        assert all(is_complete(dict(p)) for p in profiles)
        assert db.execute("""SELECT COUNT(*) FROM profiles p WHERE NOT EXISTS
                             (SELECT 1 FROM profile_interests i WHERE i.profile_id = p.id)""").fetchone()[0] == 0
        prefs = db.execute("SELECT * FROM preferences").fetchall()
        assert len(prefs) == 100
        for row in prefs:
            for field, spec in PREFERENCE_FIELDS.items():
                assert row[field] in spec["choices"], (field, row[field])


def test_emails_and_usernames_are_unique(app):
    with app.app_context():
        seed_fake_data(100)
    assert count(app, "SELECT COUNT(DISTINCT LOWER(email)) FROM users") == 100
    assert count(app, "SELECT COUNT(DISTINCT LOWER(username)) FROM users") == 100


def test_running_twice_does_not_duplicate(app, runner):
    runner.invoke(args=["seed"])
    result = runner.invoke(args=["seed"])
    assert "Added 0 fake users (100 fake users in total)" in result.output
    assert fake_users(app) == 100


def test_count_option(app, runner):
    runner.invoke(args=["seed", "--count", "10"])
    assert fake_users(app) == 10


def test_creates_some_interest_and_mutual_matches(app):
    with app.app_context():
        seed_fake_data(100)
    assert count(app, "SELECT COUNT(*) FROM connection_requests") > 50
    mutual = count(app, """SELECT COUNT(*) FROM connection_requests a JOIN connection_requests b
                           ON a.from_user_id = b.to_user_id AND a.to_user_id = b.from_user_id""")
    assert mutual > 0


def test_can_log_in_as_a_fake_user_and_use_the_app(app, client):
    with app.app_context():
        seed_fake_data(100)
        email = get_db().execute("SELECT email FROM users ORDER BY id LIMIT 1").fetchone()[0]
    token = client.get("/auth/csrf").get_json()["csrf_token"]
    resp = client.post("/auth/login", json={"email": email, "password": "password123"},
                       headers={"X-CSRF-Token": token})
    assert resp.status_code == 200
    matches = client.get("/matches").get_json()
    assert len(matches) == 20                        # default page size; 99 other people exist
    assert client.get("/find-roommates").status_code == 200
    assert client.get("/my-matches").status_code == 200


def test_remove_deletes_only_fake_users_and_their_data(app, client, runner):
    token = client.get("/auth/csrf").get_json()["csrf_token"]
    real = client.post("/auth/register", headers={"X-CSRF-Token": token}, json={
        "username": "realperson", "email": "real@washburn.edu",
        "password": "password123", "confirm_password": "password123"})
    assert real.status_code == 201
    runner.invoke(args=["seed"])

    result = runner.invoke(args=["seed", "--remove"])
    assert "Removed 100 fake users" in result.output
    assert count(app, "SELECT COUNT(*) FROM users") == 1
    assert count(app, "SELECT email FROM users") == "real@washburn.edu"
    for table in ("profiles", "profile_interests", "preferences", "connection_requests"):
        assert count(app, f"SELECT COUNT(*) FROM {table}") == 0, table
