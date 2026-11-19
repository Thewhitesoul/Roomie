import pytest


def register(client, username):
    client.post("/api/auth/logout")
    resp = client.post("/api/auth/register", json={
        "username": username,
        "email": f"{username}@washburn.edu",
        "password": "Password123!",
    })
    assert resp.status_code == 201
    return resp.get_json()["user"]["id"]


def make_user(client, username, **profile):
    """Register a user and give them a profile. Leaves them logged in."""
    register(client, username)
    body = {"name": username.title(), **profile}
    assert client.post("/api/profiles", json=body).status_code == 201


@pytest.fixture
def town(client):
    """Four users with profiles, then log in as arpan (the one searching)."""
    make_user(client, "stuti", budget=600, preferred_location="Topeka, KS",
              interests=["gaming", "cooking"])
    make_user(client, "rajju", budget=900, preferred_location="Lawrence, KS",
              interests=["hiking"])
    make_user(client, "swikar", budget=700, preferred_location="Topeka, KS",
              interests=["gaming"])
    make_user(client, "arpan", budget=700, preferred_location="Topeka, KS",
              interests=["gaming", "cooking"])
    return client


def names(resp):
    return [p["name"] for p in resp.get_json()]


# ---------- basics ----------

def test_requires_login(client):
    assert client.get("/api/matches").status_code == 401


def test_never_shows_my_own_profile(town):
    resp = town.get("/api/matches")
    assert resp.status_code == 200
    assert "Arpan" not in names(resp)
    assert len(resp.get_json()) == 3


def test_ranked_by_shared_interests(town):
    # Stuti shares 2, Swikar shares 1, Rajju shares 0
    assert names(town.get("/api/matches")) == ["Stuti", "Swikar", "Rajju"]


def test_shows_which_interests_are_shared(town):
    stuti = town.get("/api/matches").get_json()[0]
    assert stuti["shared_interests"] == ["gaming", "cooking"]
    assert stuti["shared_count"] == 2


def test_works_without_my_own_profile(client):
    make_user(client, "stuti", interests=["gaming"])
    register(client, "newbie")                 # no profile yet
    resp = client.get("/api/matches")
    assert names(resp) == ["Stuti"]
    assert resp.get_json()[0]["shared_count"] == 0


def test_no_other_users(client):
    make_user(client, "arpan")
    assert client.get("/api/matches").get_json() == []


# ---------- filters ----------

def test_filter_max_budget(town):
    assert names(town.get("/api/matches?max_budget=700")) == ["Stuti", "Swikar"]


def test_filter_min_budget(town):
    assert names(town.get("/api/matches?min_budget=800")) == ["Rajju"]

def test_filter_budget_range(town):
    assert names(town.get("/api/matches?min_budget=650&max_budget=750")) == ["Swikar"]

def test_budget_filter_skips_profiles_without_budget(client):
    make_user(client, "nobudget")              # budget left empty
    make_user(client, "arpan")
    assert client.get("/api/matches?max_budget=1000").get_json() == []

def test_filter_location_is_case_insensitive_and_partial(town):
    assert names(town.get("/api/matches?location=lawrence")) == ["Rajju"]
    assert names(town.get("/api/matches?location=TOPEKA")) == ["Stuti", "Swikar"]

def test_filter_one_interest(town):
    assert names(town.get("/api/matches?interest=hiking")) == ["Rajju"]

def test_filter_several_interests_means_any(town):
    assert names(town.get("/api/matches?interest=hiking&interest=cooking")) == ["Stuti", "Rajju"]

def test_filters_combine(town):
    assert names(town.get("/api/matches?location=topeka&max_budget=650")) == ["Stuti"]

def test_limit(town):
    assert len(town.get("/api/matches?limit=2").get_json()) == 2

def test_limit_zero_returns_nothing(town):
    assert town.get("/api/matches?limit=0").get_json() == []

@pytest.mark.parametrize("query", [
    "max_budget=abc",
    "max_budget=-5",
    "min_budget=12.5",
    "limit=ten",
    "limit=²",
    "max_budget=²",
    "min_budget=900&max_budget=500",
])
def test_bad_filters_return_400(town, query):
    resp = town.get(f"/api/matches?{query}")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_sql_injection_in_location_is_just_text(town):
    resp = town.get("/api/matches?location=' OR 1=1 --")
    assert resp.status_code == 200
    assert resp.get_json() == []