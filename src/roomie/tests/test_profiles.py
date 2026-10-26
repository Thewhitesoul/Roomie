import pytest
from app.db import get_db
def register(client, username="arpan", email="arpan@washburn.edu"):
    resp = client.post("/auth/register", json={
        "username": username, "email": email, "password": "password123",
    })
    return resp.get_json()["user"]["id"]

def create(client, **fields):
    body = {"name": "Arpan", **fields}
    return client.post("/profiles", json=body)

def profile_count(app):
    with app.app_context():
        return get_db().execute("SELECT COUNT(*) FROM profiles").fetchone()[0]

@pytest.fixture
def logged_in(client):
    """A client that is registered and logged in as 'arpan' (user 1)."""
    register(client)
    return client

def test_create_profile(logged_in):
    response = create(
        logged_in,
        bio= "Looking for a quiet roommate.",
        budget= 700,
        preferred_location= "Topeka, KS",
        interests=["gaming", "cooking"],
    )
    assert response.status_code == 201
    profile = response.get_json()
    assert profile["id"]==1
    assert profile["user_id"] == 1
    assert profile["name"] == "Arpan"
    assert profile["budget"] == 700
    assert profile["preferred_location"] == "Topeka, KS"
    assert profile["interests"] == ["gaming", "cooking"]

def test_create_profile_requires_login(client, app):
    assert create(client).status_code == 401
    assert profile_count(app) == 0


def test_user_id_comes_from_login_not_request(logged_in):
    resp = create(logged_in, user_id=999)
    assert resp.get_json()["user_id"] == 1


def test_only_one_profile_per_user(logged_in, app):
    create(logged_in)
    assert create(logged_in, name="Second Try").status_code == 409
    assert profile_count(app) == 1


def test_create_profile_requires_name(logged_in):
    assert logged_in.post("/profiles", json={}).status_code == 400
    assert create(logged_in, name="   ").status_code == 400


def test_create_profile_rejects_negative_budget(logged_in):
    assert create(logged_in, budget=-100).status_code == 400


@pytest.mark.parametrize("bad_budget", ["700", 70.5, True])
def test_create_profile_rejects_non_number_budget(logged_in, bad_budget):
    assert create(logged_in, budget=bad_budget).status_code == 400


def test_create_profile_rejects_bad_interests(logged_in):
    assert create(logged_in, interests="gaming").status_code == 400
    assert create(logged_in, interests=["x"] * 11).status_code == 400


def test_interests_are_cleaned(logged_in):
    response = create(logged_in, interests=[" Gaming ", "gaming", "Cooking"])
    assert response.get_json()["interests"] == ["gaming", "cooking"]

def test_get_all_profiles(client):
    register(client, "arpan", "arpan@washburn.edu")
    create(client, name="Arpan")
    client.post("/auth/logout")

    register(client, "stuti", "stuti@washburn.edu")
    create(client, name="Stuti")

    response = client.get("/profiles")
    assert response.status_code == 200
    assert [p["name"] for p in response.get_json()] == ["Arpan", "Stuti"]

def test_get_single_profile(logged_in):
    profile_id = create(logged_in, interests=["gaming"]).get_json()["id"]
    response = logged_in.get(f"/profiles/{profile_id}")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Arpan"
    assert response.get_json()["interests"]==["gaming"]

def test_get_missing_profile(logged_in):
    response = logged_in.get("/profiles/999")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Profile not found"}

def test_viewing_requires_login(client):
    assert client.get("/profiles").status_code == 401
    assert client.get("/profiles/1").status_code == 401


def test_get_my_profile(logged_in):
    assert logged_in.get("/profiles/me").status_code == 404
    create(logged_in)
    assert logged_in.get("/profiles/me").get_json()["name"] == "Arpan"
    
def test_update_my_profile(logged_in):
    create(logged_in, budget=700)
    response = logged_in.put("/profiles/me", json={"budget": 650, "bio": "Night owl."})
    assert response.status_code == 200
    assert response.get_json()["budget"] == 650
    assert response.get_json()["bio"] == "Night owl."
    assert response.get_json()["name"] == "Arpan"          # unchanged fields stay


def test_update_replaces_interests(logged_in):
    create(logged_in, interests=["gaming", "cooking"])
    response = logged_in.put("/profiles/me", json={"interests": ["hiking"]})
    assert response.get_json()["interests"] == ["hiking"]


def test_update_cannot_change_owner_or_id(logged_in):
    create(logged_in)
    response = logged_in.put("/profiles/me", json={"user_id": 999, "id": 999})
    assert response.get_json()["user_id"] == 1
    assert response.get_json()["id"] == 1


def test_update_validates(logged_in):
    create(logged_in)
    assert logged_in.put("/profiles/me", json={"budget": -5}).status_code == 400
    assert logged_in.put("/profiles/me", json={"name": ""}).status_code == 400


def test_update_without_profile(logged_in):
    assert logged_in.put("/profiles/me", json={"bio": "hi"}).status_code == 404


def test_cannot_edit_someone_elses_profile(client):
    register(client, "arpan", "arpan@washburn.edu")
    create(client, name="Arpan")
    client.post("/auth/logout")

    register(client, "stuti", "stuti@washburn.edu")
    client.put("/profiles/me", json={"name": "Hacked"})
    assert client.get("/profiles/1").get_json()["name"] == "Arpan"