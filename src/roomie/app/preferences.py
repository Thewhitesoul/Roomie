from flask import Blueprint, flash, g, jsonify, request

from .auth import login_required
from .db import SQLITE_MAX_INTEGER, get_db

preferences_bp = Blueprint(
    "preferences", __name__, url_prefix="/preferences"
)

TEXT_FIELDS = (
    "cleanliness",
    "sleep_schedule",
    "study_habits",
    "smoking_preference",
    "pet_preference",
)
FIELDS = (*TEXT_FIELDS, "budget")
MAX_BUDGET = 9223372036854775807


def _mine():
    row = get_db().execute(
        "SELECT * FROM preferences WHERE user_id = ?",
        (g.user["id"],),
    ).fetchone()

    if row:
        return dict(row)

    return {"user_id": g.user["id"], **dict.fromkeys(FIELDS)}


@preferences_bp.get("/me")
@login_required
def get_preferences():
    return jsonify(_mine())


@preferences_bp.get("/profile/<int:profile_id>")
@login_required
def get_profile_preferences(profile_id):
    """Only the six shareable lifestyle fields, addressed by profile ID."""
    if profile_id > SQLITE_MAX_INTEGER:
        return jsonify(error="Profile not found."), 404
    # LEFT JOIN distinguishes an existing profile with no preferences (nulls)
    # from a nonexistent profile (404). Never use the viewer's session user ID.
    columns = ", ".join(f"pref.{field}" for field in FIELDS)
    row = get_db().execute(
        f"SELECT {columns} FROM profiles AS profile "
        "LEFT JOIN preferences AS pref ON pref.user_id = profile.user_id "
        "WHERE profile.id = ?",
        (profile_id,),
    ).fetchone()
    if row is None:
        return jsonify(error="Profile not found."), 404
    response = jsonify({field: row[field] for field in FIELDS})
    response.headers['Cache-Control'] = 'no-store'
    return response


@preferences_bp.put("/me")
@login_required
def save_preferences():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify(error="Expected a JSON object."), 400

    if "user_id" in data or "id" in data:
        return jsonify(
            error="Preferences ownership cannot be changed."
        ), 400

    if set(data) - set(FIELDS):
        return jsonify(error="Unknown preference field."), 400

    cleaned = {}

    for field, value in data.items():
        if field == "budget":
            if value is not None and (
                type(value) is not int
                or not 0 <= value <= MAX_BUDGET
            ):
                return jsonify(
                    error="Budget must be a nonnegative whole-dollar integer or null."
                ), 400

        elif value is not None:
            if (
                not isinstance(value, str)
                or not value.strip()
                or len(value.strip()) > 100
                or any(ord(c) < 32 for c in value)
            ):
                return jsonify(
                    error=f"{field} must be nonempty text up to 100 characters, or null."
                ), 400

            value = value.strip()

        cleaned[field] = value

    values = _mine()
    values.update(cleaned)

    db = get_db()
    columns = ", ".join(FIELDS)
    updates = ", ".join(
        f"{field} = excluded.{field}" for field in FIELDS
    )

    with db:
        db.execute(
            f"INSERT INTO preferences (user_id, {columns}) "
            "VALUES (?, ?, ?, ?, ?, ?, ?) "
            f"ON CONFLICT(user_id) DO UPDATE SET {updates}",
            (g.user["id"], *(values[field] for field in FIELDS)),
        )

    flash("Preferences saved.")
    return jsonify(_mine())
