from app import storage
def register(client, username="arpan", email="arpan@washburn.edu", password="password123"):
    return client.post("/auth/register", json={
        "username": username, "email": email, "password": password,
    })

def login(client, email="arpan@washburn.edu", password="password123"):
    return client.post("/auth/login", json={"email": email, "password": password})
#register
def test_register_success(client, app):
    resp = register(client)
    assert resp.status_code == 201
    assert resp.get_json()["user"]["id"] == "user-001"
    saved = storage.read_json("users.json")[0]
    assert saved["email"] == "arpan@washburn.edu"
    assert saved["password_hash"] != "password123"    
    
def test_register_does_not_return_password_hash(client):
    assert "password_hash" not in register(client).get_json()["user"]

def test_register_ids_count_up(client):
    register(client)
    resp = register(client, username="stuti", email="stuti@washburn.edu")
    assert resp.get_json()["user"]["id"] == "user-002"

def test_register_logs_user_in(client):
    register(client)
    assert client.get("/auth/me").status_code == 200

def test_register_duplicate_email(client):
    register(client)
    resp = register(client, username="other", email="ARPAN@washburn.edu")
    assert resp.status_code == 409
    assert len(storage.read_json("users.json")) == 1

def test_register_duplicate_username(client):
    register(client)
    resp = register(client, username="ARPAN", email="other@washburn.edu")
    assert resp.status_code == 409

def test_register_short_password(client):
    assert register(client, password="short").status_code == 400

def test_register_bad_email(client):
    assert register(client, email="not-an-email").status_code == 400

def test_register_bad_username(client):
    assert register(client, username="a b").status_code == 400

def test_register_missing_fields(client):
    assert client.post("/auth/register", json={}).status_code == 400

def test_register_works_with_html_form(client):
    resp = client.post("/auth/register", data={
        "username": "rajju", "email": "rajju@washburn.edu", "password": "password123",
    })
    assert resp.status_code == 201
# login/logout
def test_login_success(client):
    register(client)
    client.post("/auth/logout")
    resp = login(client)
    assert resp.status_code == 200
    assert client.get("/auth/me").get_json()["user"]["username"] == "arpan"

def test_login_email_is_case_insensitive(client):
    register(client)
    assert login(client, email="Arpan@Washburn.edu").status_code == 200
    
def test_login_wrong_password(client):
    register(client)
    client.post("/auth/logout")
    resp = login(client, password="wrongpass1")
    assert resp.status_code == 401
    assert client.get("/auth/me").status_code == 401
    
def test_login_unknown_email_same_message(client):
    register(client)
    wrong_pw = login(client, password="wrongpass1").get_json()
    no_user = login(client, email="nobody@washburn.edu").get_json()
    assert wrong_pw == no_user

def test_logout(client):
    register(client)
    assert client.post("/auth/logout").status_code == 200
    assert client.get("/auth/me").status_code == 401

def test_me_requires_login(client):
    resp = client.get("/auth/me")
    assert resp.status_code == 401
    assert "error" in resp.get_json()