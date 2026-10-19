import re
from email_validator import validate_email
from flask import Blueprint, jsonify, g,  session
from werkzeug.security import check_password_hash, generate_password_hash
from . import storage
import functools
from datetime import datetime, timezone
bp= Blueprint("auth", __name__, url_prefix="/auth")
USERS_FILE = "users.json"
USERNAME_RE = re.compile(r"^[A-Za-z0-9_]{3,30}$")
MIN_PASSWORD_LENGTH = 8

def get_input():
    return request.get_json(silent=True)

def next_user_id(users):
    numbers = [int(u["id"].split("-")[1]) for u in users if u.get("id", "").startswith("user-")]
    return f"user-{max(numbers, default=0) + 1:03d}"    

def public(user):
        return {k: user[k] for k in ("id", "username", "email", "created_at")}
    
def find_user_by_id(user_id):
    return next((u for u in storage.read_json(USERS_FILE) if u["id"] == user_id), None)

def _error(message, status):
    return jsonify({"error": message}), status

@bp.before_app_request
def load_logged_in_user():
    """Runs before every request: puts the current user (or None) in g.user."""
    user_id = session.get("user_id")
    g.user = find_user_by_id(user_id) if user_id else None


def login_required(view):
    """Put @login_required above any route that needs a logged-in user."""
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return _error("You must be logged in.", 401)
        return view(*args, **kwargs)
    return wrapped

@bp.post("/register")
def register():
    data = get_input()
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if not USERNAME_RE.match(username):
        return _error("Username must be 3-30 letters, numbers, or underscores.", 400)
    validated_email = validate_email(email)
    if not validated_email:
        return _error("Enter a valid email address.", 400)
    email = validated_email
    if len(password) < MIN_PASSWORD_LENGTH:
        return _error(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.", 400)

    # Lock so two people registering at once can't overwrite each other.
    with storage.storage_lock:
        users = storage.read_json(USERS_FILE)

        if any(u["email"] == email for u in users):
            return _error("An account with that email already exists.", 409)
        if any(u["username"].lower() == username.lower() for u in users):
            return _error("That username is taken.", 409)

        user = {
            "id": next_user_id(users),
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        users.append(user)
        storage.write_json(USERS_FILE, users)

    session.clear()
    session["user_id"] = user["id"]
    return jsonify({"user": public(user)}), 201


@bp.post("/login")
def login():
    data = get_input()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = next((u for u in storage.read_json(USERS_FILE) if u["email"] == email), None)

    # Same message either way, so nobody can test which emails have accounts.
    if user is None or not check_password_hash(user["password_hash"], password):
        return _error("Invalid email or password.", 401)

    session.clear()  # start a fresh session on every login
    session["user_id"] = user["id"]
    return jsonify({"user": public(user)}), 200


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out."}), 200


@bp.get("/me")
@login_required
def me():
    """Lets the front end ask 'who is logged in right now?'"""
    return jsonify({"user": public(g.user)}), 200