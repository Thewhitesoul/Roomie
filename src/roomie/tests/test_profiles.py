
def test_create_profile(client):
    response = client.post(
        "/profiles",
        json={
            "user_id": "user-001",
            "name": "Arpan",
            "bio": "Looking for a quiet roommate.",
            "budget": 700,
            "preferred_location": "Topeka, KS",
            "interests": ["gaming", "cooking"],
        },
    )
    assert response.status_code == 201
    profile = response.get_json()
    assert profile["id"]
    assert profile["user_id"] == "user-001"
    assert profile["name"] == "Arpan"
    assert profile["budget"] == 700

def test_get_all_profiles(client):
    client.post(
        "/profiles",
        json={"user_id": "user-001", "name": "Arpan"},
    )
    client.post(
        "/profiles",
        json={"user_id": "user-002", "name": "Test User"},
    )
    response = client.get("/profiles")
    assert response.status_code == 200
    assert len(response.get_json()) == 2

def test_get_single_profile(client):
    create_response = client.post(
        "/profiles",
        json={"user_id": "user-001", "name": "Arpan"},
    )
    profile_id = create_response.get_json()["id"]
    response = client.get(f"/profiles/{profile_id}")
    assert response.status_code == 200
    assert response.get_json()["name"] == "Arpan"

def test_get_missing_profile(client):
    response = client.get("/profiles/nonexistent-id")
    assert response.status_code == 404
    assert response.get_json() == {"error": "Profile not found"}

def test_create_profile_requires_name(client):
    response = client.post(
        "/profiles",
        json={"user_id": "user-001"},
    )
    assert response.status_code == 400

def test_create_profile_rejects_negative_budget(client):
    response = client.post(
        "/profiles",
        json={
            "user_id": "user-001",
            "name": "Arpan",
            "budget": -100,
        },
    )
    assert response.status_code == 400