import os
import pytest 
from app import create_app, storage
def test_health(client):
    resp =client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json() =={"status":"ok"} 
    
def test_files_created_empty(app):
    for filename in storage.DEFAULT_FILES:
        assert storage.read_json(filename) == []
        
def test_write_then_read(app):
    user = {"id": "user-001", "username": "testuser", "email": "test@example.com"}
    storage.write_json("users.json", [user])
    assert storage.read_json("users.json") == [user]
    
def test_restart_does_not_wipe_data(tmp_path):
    config = {
        "TESTING": True,
        "DATA_DIR": str(tmp_path),
    }

    app = create_app(config)

    with app.app_context():
        storage.write_json("users.json", [{"id": "user-001"}])

    restarted_app = create_app(config)

    with restarted_app.app_context():
        assert storage.read_json("users.json") == [
            {"id": "user-001"}
        ]

def test_missing_file_is_recreated(app):
    os.remove(os.path.join(app.config["DATA_DIR"], "users.json"))
    assert storage.read_json("users.json") == []

def test_unicode_is_kept(app):
    storage.write_json("users.json", [{"name": "नमस्ते"}])
    assert storage.read_json("users.json")[0]["name"] == "नमस्ते"


def test_no_temp_files_left_behind(app):
    storage.write_json("users.json", [{"id": "user-001"}])

    leftovers = [
        f for f in os.listdir(app.config["DATA_DIR"])
        if f.endswith(".tmp") or f.endswith(".temp")
    ]

    assert leftovers == []

def test_unknown_file_rejected(app):
    with pytest.raises(ValueError):
        storage.read_json("passwords.json")