import pytest


def register(client):
    return client.post("/api/auth/register", json={
        "username": "sam_user", "email": "sam@washburn.edu", "password": "Password123!",
    })


def nav(html):
    return html.split("<nav", 1)[1].split("</nav>", 1)[0]


@pytest.mark.parametrize("path", ["/", "/matches", "/login", "/register", "/profiles/1"])
def test_public_pages_logged_out(client, path):
    resp = client.get(path)
    assert resp.status_code == 200
    menu = nav(resp.text)
    for label in ("Home", "Find roommates", "Log in", "Get started"):
        assert label in menu
    for label in ("My profile", "Preferences", "account-dropdown"):
        assert label not in menu
    assert 'href="/register"' in menu


def test_register_page(client):
    assert "Create your account" in client.get("/register").text


def test_missing_profile_page(client):
    assert client.get("/profiles/999").status_code == 404


def test_static_files_are_served(client):
    assert client.get("/static/style.css").status_code == 200
    assert client.get("/static/app.js").status_code == 200


@pytest.mark.parametrize("path", ["/profile", "/preferences"])
def test_private_pages_redirect_when_logged_out(client, path):
    resp = client.get(path)
    assert resp.status_code == 302
    assert resp.location == "/login?next=" + path


def test_nav_when_logged_in(client):
    register(client)
    menu = nav(client.get("/").text)
    assert "sam_user" in menu
    assert 'href="/profile"' in menu
    assert 'href="/preferences"' in menu
    assert 'action="/logout"' in menu
    assert "Get started" not in menu
    assert ">Log in<" not in menu


@pytest.mark.parametrize("path", ["/profile", "/preferences"])
def test_private_pages_when_logged_in(client, path):
    register(client)
    assert client.get(path).status_code == 200


def test_logout_page(client):
    register(client)
    resp = client.post("/logout")
    assert resp.status_code == 302
    assert resp.location == "/"
    assert client.get("/profile").status_code == 302   # logged out again


def test_pages_and_api_do_not_clash(client):
    # /matches is the HTML page; /api/matches is the JSON API
    assert "text/html" in client.get("/matches").content_type
    assert client.get("/api/matches").status_code == 401
