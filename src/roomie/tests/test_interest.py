import pytest


def login_as(client, username, make_profile=True):
    """Register (first time) or log in as username. Returns their user id."""
    client.post("/auth/logout")
    email = f"{username}@washburn.edu"
    resp = client.post("/auth/register", json={
        "username": username, "email": email, "password": "password123",
    })
    if resp.status_code == 409:   # already registered -> just log in
        resp = client.post("/auth/login", json={"email": email, "password": "password123"})
    elif make_profile:
        client.post("/profiles", json={"name": username.title()})
    return resp.get_json()["user"]["id"]


@pytest.fixture
def people(client):
    """arpan=1, stuti=2, rajju=3, each with a profile. Ends logged in as arpan."""
    ids = {name: login_as(client, name) for name in ("arpan", "stuti", "rajju")}
    login_as(client, "arpan")
    return ids


def user_ids(resp):
    return [p["user_id"] for p in resp.get_json()]


# ---------- sending ----------
def test_requires_login(client):
    assert client.post("/interest/1").status_code == 401
    assert client.get("/interest/sent").status_code == 401
    assert client.get("/interest/received").status_code == 401
    assert client.get("/interest/mutual").status_code == 401
    assert client.delete("/interest/1").status_code == 401


def test_show_interest(client, people):
    resp = client.post(f"/interest/{people['stuti']}")
    assert resp.status_code == 201
    assert resp.get_json() == {"to_user_id": people["stuti"], "mutual": False}


def test_cannot_show_interest_in_self(client, people):
    resp = client.post(f"/interest/{people['arpan']}")
    assert resp.status_code == 400


def test_unknown_user(client, people):
    resp = client.post("/interest/999")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "User not found"



def test_duplicate_interest(client, people):
    client.post(f"/interest/{people['stuti']}")
    resp = client.post(f"/interest/{people['stuti']}")
    assert resp.status_code == 409


def test_second_person_gets_mutual_true(client, people):
    client.post(f"/interest/{people['stuti']}")       # arpan -> stuti
    login_as(client, "stuti")
    resp = client.post(f"/interest/{people['arpan']}")  # stuti -> arpan
    assert resp.get_json()["mutual"] is True


# ---------- lists ----------
def test_sent_list(client, people):
    client.post(f"/interest/{people['stuti']}")
    client.post(f"/interest/{people['rajju']}")
    assert sorted(user_ids(client.get("/interest/sent"))) == [people["stuti"], people["rajju"]]


def test_received_list(client, people):
    client.post(f"/interest/{people['stuti']}")       # arpan -> stuti
    login_as(client, "rajju")
    client.post(f"/interest/{people['stuti']}")       # rajju -> stuti

    login_as(client, "stuti")
    got = client.get("/interest/received").get_json()
    assert sorted(p["user_id"] for p in got) == [people["arpan"], people["rajju"]]
    assert {p["name"] for p in got} == {"Arpan", "Rajju"}


def test_received_does_not_include_sent(client, people):
    client.post(f"/interest/{people['stuti']}")
    assert client.get("/interest/received").get_json() == []


def test_list_shows_safe_fields_only(client, people):
    client.post(f"/interest/{people['stuti']}")
    person = client.get("/interest/sent").get_json()[0]
    assert set(person) == {"user_id", "username", "name", "profile_id", "since"}
    assert person["username"] == "stuti"


def test_person_without_profile_still_listed(client, people):
    newbie = login_as(client, "newbie", make_profile=False)
    login_as(client, "arpan")
    client.post(f"/interest/{newbie}")
    person = client.get("/interest/sent").get_json()[0]
    assert person["username"] == "newbie"
    assert person["name"] is None
    assert person["profile_id"] is None


# ---------- mutual ----------
def test_mutual_needs_both_sides(client, people):
    client.post(f"/interest/{people['stuti']}")       # only one direction
    assert client.get("/interest/mutual").get_json() == []

def test_mutual_match(client, people):
    client.post(f"/interest/{people['stuti']}")       # arpan -> stuti
    client.post(f"/interest/{people['rajju']}")       # arpan -> rajju (one-way)
    login_as(client, "stuti")
    client.post(f"/interest/{people['arpan']}")       # stuti -> arpan

    # Both sides see each other, and only each other.
    assert user_ids(client.get("/interest/mutual")) == [people["arpan"]]
    login_as(client, "arpan")
    assert user_ids(client.get("/interest/mutual")) == [people["stuti"]]

# ---------- withdraw ----------
def test_withdraw(client, people):
    client.post(f"/interest/{people['stuti']}")
    assert client.delete(f"/interest/{people['stuti']}").status_code == 200
    assert client.get("/interest/sent").get_json() == []
    # Can show interest again after withdrawing.
    assert client.post(f"/interest/{people['stuti']}").status_code == 201


def test_withdraw_nothing(client, people):
    resp = client.delete(f"/interest/{people['stuti']}")
    assert resp.status_code == 404
    assert resp.get_json()["error"] == "You haven't shown interest in this user."


def test_withdraw_breaks_mutual(client, people):
    client.post(f"/interest/{people['stuti']}")
    login_as(client, "stuti")
    client.post(f"/interest/{people['arpan']}")
    client.delete(f"/interest/{people['arpan']}")
    assert client.get("/interest/mutual").get_json() == []


def test_cannot_withdraw_someone_elses_interest(client, people):
    client.post(f"/interest/{people['stuti']}")       # arpan -> stuti
    login_as(client, "rajju")
    # rajju tries to delete arpan's interest; it only deletes rajju's own rows
    assert client.delete(f"/interest/{people['stuti']}").status_code == 404
    login_as(client, "stuti")
    assert user_ids(client.get("/interest/received")) == [people["arpan"]]