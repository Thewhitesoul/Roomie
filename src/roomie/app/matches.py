"""Find possible roommates: filter other users' profiles and rank by shared interests."""
from flask import Blueprint, g, jsonify, request

from .auth import login_required
from .db import get_db

matches_bp = Blueprint("matches", __name__, url_prefix="/matches")

DEFAULT_LIMIT = 20
MAX_LIMIT = 50


def _error(message, status):
    return jsonify({"error": message}), status


def _whole_number(name):
    """Read an optional whole-number query parameter. Returns (value, error)."""
    raw = request.args.get(name)
    if raw is None or raw.strip() == "":
        return None, None
    if not raw.strip().isdigit():
        return None, f"{name} must be a whole number of 0 or more."
    return int(raw), None


def _interests_for(profile_id):
    rows = get_db().execute(
        "SELECT interest FROM profile_interests WHERE profile_id = ? ORDER BY rowid",
        (profile_id,),
    )
    return [r["interest"] for r in rows]


@matches_bp.get("")
@login_required
def find_matches():
    # ---- read and check the filters ----
    max_budget, err = _whole_number("max_budget")
    if err:
        return _error(err, 400)
    min_budget, err = _whole_number("min_budget")
    if err:
        return _error(err, 400)
    if min_budget is not None and max_budget is not None and min_budget > max_budget:
        return _error("min_budget cannot be more than max_budget.", 400)

    limit, err = _whole_number("limit")
    if err:
        return _error(err, 400)
    limit = min(limit or DEFAULT_LIMIT, MAX_LIMIT)

    location = (request.args.get("location") or "").strip()
    # ?interest=gaming&interest=cooking -> profiles with ANY of these interests
    wanted = [i.strip().lower() for i in request.args.getlist("interest") if i.strip()]

    # ---- build the query ----
    # Every value goes in with a ? placeholder, never pasted into the SQL text.
    sql = "SELECT * FROM profiles WHERE user_id != ?"
    params = [g.user["id"]]                       # never show your own profile

    if max_budget is not None:
        sql += " AND budget IS NOT NULL AND budget <= ?"
        params.append(max_budget)
    if min_budget is not None:
        sql += " AND budget IS NOT NULL AND budget >= ?"
        params.append(min_budget)
    if location:
        sql += " AND LOWER(preferred_location) LIKE ?"
        params.append(f"%{location.lower()}%")
    if wanted:
        placeholders = ", ".join("?" for _ in wanted)
        sql += (" AND id IN (SELECT profile_id FROM profile_interests"
                f" WHERE interest IN ({placeholders}))")
        params.extend(wanted)

    rows = get_db().execute(sql, params).fetchall()

    # ---- rank by how many interests they share with me ----
    me = get_db().execute("SELECT id FROM profiles WHERE user_id = ?", (g.user["id"],)).fetchone()
    my_interests = set(_interests_for(me["id"])) if me else set()

    results = []
    for row in rows:
        interests = _interests_for(row["id"])
        shared = [i for i in interests if i in my_interests]
        results.append({
            "id": row["id"],
            "user_id": row["user_id"],
            "name": row["name"],
            "bio": row["bio"],
            "budget": row["budget"],
            "preferred_location": row["preferred_location"],
            "interests": interests,
            "shared_interests": shared,
            "shared_count": len(shared),
        })

    # Most shared interests first; ties keep the oldest profile first.
    results.sort(key=lambda p: (-p["shared_count"], p["id"]))
    return jsonify(results[:limit]), 200