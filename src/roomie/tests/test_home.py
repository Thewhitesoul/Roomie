from html.parser import HTMLParser
from pathlib import Path

import pytest

from app import create_app


class HomepageLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.pages = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append(attrs["href"])
        elif tag == "script" and "src" in attrs:
            self.assets.append(attrs["src"])
        elif tag == "a" and attrs.get("href", "").startswith("/"):
            self.pages.append(attrs["href"])


def test_homepage_and_assets(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.mimetype == "text/html"
    assert b"Find your people | Roomie" in response.data
    assert b"floating-card floating-3" in response.data
    links = HomepageLinks()
    links.feed(response.text)
    assert links.assets == ["/static/style.css", "/static/app.js"]
    static_root = Path(__file__).resolve().parents[2] / "static"
    for url in links.assets:
        asset = client.get(url)
        assert asset.status_code == 200
        assert asset.data == (static_root / url.rsplit("/", 1)[1]).read_bytes()
    for url in links.pages:
        assert client.get(url, follow_redirects=True).status_code == 200


def test_homepage_does_not_require_or_create_database(tmp_path):
    database = tmp_path / "not-created.sqlite"
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    assert app.test_client().get("/").status_code == 200
    assert not database.exists()


@pytest.mark.parametrize("path", ["/find-roommates", "/roommate/1"])
def test_matching_pages_require_login_and_are_read_only(client, path):
    response = client.get(path)
    assert response.status_code == 302
    assert response.location == '/login'
    assert client.post(path).status_code == 405
    with client.session_transaction() as session:
        assert "user_id" not in session


def test_backend_routes_and_security_remain(client):
    assert client.get("/health").get_json() == {"status": "ok"}
    for path in ("/auth/me", "/profiles", "/profiles/1", "/matches", "/interest/sent"):
        response = client.get(path)
        assert response.status_code == 401
        assert response.is_json


def test_homepage_preserves_existing_authenticated_session(client):
    response = client.post("/auth/register", json={
        "username": "homepage_user", "email": "homepage@washburn.edu",
        "password": "password123",
    })
    assert response.status_code == 201
    before = client.get("/auth/me").get_json()
    assert client.get("/").status_code == 200
    assert client.get("/login").status_code == 200
    assert client.get("/auth/me").get_json() == before
