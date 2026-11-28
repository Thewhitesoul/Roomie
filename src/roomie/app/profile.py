import sqlite3

from flask import Blueprint, flash, jsonify, request, g
from .auth import login_required
from .db import SQLITE_MAX_INTEGER, get_db
from .profile_state import MIN_AGE, MAX_AGE, HOUSING_LABELS
profiles_bp = Blueprint("profiles", __name__,url_prefix="/profiles")
MAX_NAME = 60
MAX_BIO = 500
MAX_LOCATION = 100
MAX_INTERESTS = 10
MAX_INTEREST_LENGTH = 30
def _error(message, status):
    return jsonify({"error": message}), status

def _clean(data, creating):
    """Check the input. Returns (cleaned_fields, None) or (None, error_message).
    Only supported profile fields are read; user_id and id are ignored."""
    cleaned = {}

    if "name" in data or creating:
        name = data.get("name")
        if not isinstance(name, str) or not name.strip():
            return None, "Name is required."
        if len(name.strip()) > MAX_NAME:
            return None, f"Name must be {MAX_NAME} characters or fewer."
        cleaned["name"] = name.strip()

    if "age" in data or creating:
        age = data.get("age")
        if isinstance(age, bool) or not isinstance(age, int) or not MIN_AGE <= age <= MAX_AGE:
            return None, f"Age must be a whole number from {MIN_AGE} to {MAX_AGE}."
        cleaned["age"] = age

    if "housing_status" in data or creating:
        housing = data.get("housing_status")
        if not isinstance(housing, str) or housing not in HOUSING_LABELS:
            return None, "Choose whether you need housing or already have housing."
        cleaned["housing_status"] = housing

    if "bio" in data:
        bio = data.get("bio")
        if bio is None:
            bio = ""
        if not isinstance(bio, str) or len(bio) > MAX_BIO:
            return None, f"Bio must be text, {MAX_BIO} characters or fewer."
        cleaned["bio"] = bio.strip()

    if "budget" in data:
        budget = data.get("budget")
        # bool is a kind of int in Python, so rule it out explicitly.
        if budget is not None and (isinstance(budget, bool) or not isinstance(budget, int)
                                   or not 0 <= budget <= SQLITE_MAX_INTEGER):
            return None, f"Budget must be a whole number from 0 to {SQLITE_MAX_INTEGER}."
        cleaned["budget"] = budget

    if "preferred_location" in data or creating:
        loc = data.get("preferred_location")
        if not isinstance(loc, str) or not loc.strip() or len(loc) > MAX_LOCATION:
            return None, f"Preferred location is required and must be text, {MAX_LOCATION} characters or fewer."
        cleaned["preferred_location"] = loc.strip()

    if "interests" in data:
        interests = data.get("interests")
        if interests is None:
            interests = []
        if (not isinstance(interests, list)
                or len(interests) > MAX_INTERESTS
                or not all(isinstance(i, str) and 0 < len(i.strip()) <= MAX_INTEREST_LENGTH for i in interests)):
            return None, f"Interests must be a list of up to {MAX_INTERESTS} short words."
        # Lowercase and remove duplicates, keeping the original order.
        cleaned["interests"] = list(dict.fromkeys(i.strip().lower() for i in interests))

    return cleaned, None

def _to_dict(row):
    """Turn a profiles row into JSON, with its interests attached."""
    interests = [r["interest"] for r in get_db().execute(
        "SELECT interest FROM profile_interests WHERE profile_id = ? ORDER BY rowid", (row["id"],)
    )]
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "age": row["age"],
        "housing_status": row["housing_status"],
        "bio": row["bio"],
        "budget": row["budget"],
        "preferred_location": row["preferred_location"],
        "interests": interests,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

def _save_interests(db, profile_id, interests):
    db.execute("DELETE FROM profile_interests WHERE profile_id = ?", (profile_id,))
    db.executemany(
        "INSERT INTO profile_interests (profile_id, interest) VALUES (?, ?)",
        [(profile_id, i) for i in interests],
    )

def _my_profile():
    return get_db().execute("SELECT * FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()


@profiles_bp.post("")
@login_required
def create_profile():
    if not request.is_json:
        return _error("Send a JSON request.", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Request body must be a valid JSON object.", 400)
    cleaned, err = _clean(data, creating=True)
    if err:
        return _error(err, 400)

    if _my_profile():
        return _error("You already have a profile. Use PUT /profiles/me to edit it.", 409)

    db = get_db()
    try:
        with db:  # The profile and its interests are one atomic write.
            cur = db.execute(
                """INSERT INTO profiles (user_id, name, bio, budget, preferred_location, age, housing_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (g.user["id"],                       # always from the session, never the request
                cleaned["name"],
                cleaned.get("bio", ""),
                cleaned.get("budget"),
                cleaned["preferred_location"], cleaned["age"], cleaned["housing_status"]),
            )
            _save_interests(db, cur.lastrowid, cleaned.get("interests", []))
    except sqlite3.IntegrityError:
        if _my_profile() is not None:
            return _error("You already have a profile. Reload to edit it.", 409)
        raise

    row = db.execute("SELECT * FROM profiles WHERE id = ?", (cur.lastrowid,)).fetchone()
    flash("Profile created. Welcome home!")
    return jsonify(_to_dict(row)), 201
@profiles_bp.get("")
@login_required
def list_profiles():
    rows = get_db().execute("SELECT * FROM profiles ORDER BY id").fetchall()
    return jsonify([_to_dict(r) for r in rows]), 200

@profiles_bp.get("/me")
@login_required
def get_my_profile():
    row = _my_profile()
    if row is None:
        return _error("Profile not found", 404)
    return jsonify(_to_dict(row)), 200

@profiles_bp.put("/me")
@login_required
def update_my_profile():
    if not request.is_json:
        return _error("Send a JSON request.", 415)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _error("Request body must be a valid JSON object.", 400)
    cleaned, err = _clean(data, creating=False)
    if err:
        return _error(err, 400)

    row = _my_profile()
    if row is None:
        return _error("Profile not found", 404)

    db = get_db()
    interests = cleaned.pop("interests", None)
    if cleaned:
        # Column names come from our own fixed list in _clean, never from the user,
        # so building the SET part this way is safe. Values still use ? placeholders.
        set_sql = ", ".join(f"{col} = ?" for col in cleaned)
        db.execute(
            f"UPDATE profiles SET {set_sql}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (*cleaned.values(), row["id"]),
        )
    if interests is not None:
        _save_interests(db, row["id"], interests)
        db.execute("UPDATE profiles SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (row["id"],))
    db.commit()

    row = db.execute("SELECT * FROM profiles WHERE id = ?", (row["id"],)).fetchone()
    flash("Profile saved.")
    return jsonify(_to_dict(row)), 200

@profiles_bp.get("/<int:profile_id>")
@login_required
def get_profile(profile_id):
    if profile_id > SQLITE_MAX_INTEGER:
        return _error("Profile not found", 404)
    row = get_db().execute("SELECT * FROM profiles WHERE id = ?", (profile_id,)).fetchone()
    if row is None:
        return _error("Profile not found", 404)
    return jsonify(_to_dict(row)), 200
