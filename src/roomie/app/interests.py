"""Show interest in connecting with another user .
A "mutual match" is when two users have both shown interest in each other.
Rows live in the connection_requests table: one row = from_user -> to_user.
"""
import sqlite3

from flask import Blueprint, g, jsonify

from .auth import login_required
from .db import get_db

interest_bp = Blueprint("interest", __name__, url_prefix="/interest")


def _error(message, status):
    return jsonify({"error": message}), status


def _person(row):
    """What the front end gets for each person in a list. No email or password."""
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "name": row["name"], # None if they haven't made a profile yet
        "profile_id": row["profile_id"],
        "since": row["created_at"],
    }

def _is_mutual(db, me, other):
    return db.execute(
        "SELECT 1 FROM connection_requests WHERE from_user_id = ? AND to_user_id = ?",
        (other, me),
    ).fetchone() is not None
    
# ---------- send / take back ----------
@interest_bp.post("/<int:user_id>")
@login_required
def show_interest(user_id):
    me = g.user["id"]
    db = get_db()
    if user_id == me:
        return _error("You can't show interest in yourself.", 400)
    if db.execute("SELECT 1 FROM users WHERE id = ?", (user_id,)).fetchone() is None:
        return _error("User not found", 404)

    try:
        db.execute(
            "INSERT INTO connection_requests (from_user_id, to_user_id) VALUES (?, ?)",
            (me, user_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        # The UNIQUE(from_user_id, to_user_id) rule in schema.sql caught a repeat.
        return _error("You already showed interest in this user.", 409)

    return jsonify({"to_user_id": user_id, "mutual": _is_mutual(db, me, user_id)}), 201

@interest_bp.delete("/<int:user_id>")
@login_required
def withdraw_interest(user_id):
    db = get_db()
    cur = db.execute(
        "DELETE FROM connection_requests WHERE from_user_id = ? AND to_user_id = ?",
        (g.user["id"], user_id),
    )
    db.commit()
    if cur.rowcount == 0:
        return _error("You haven't shown interest in this user.", 404)
    return jsonify({"message": "Interest withdrawn."}), 200


# ---------- lists ----------
# Each query joins users (for username) and profiles (for name). LEFT JOIN keeps
# people who haven't created a profile yet; their name and profile_id are None.

@interest_bp.get("/sent")
@login_required
def sent():
    """People I showed interest in."""
    rows = get_db().execute(
        """SELECT u.id AS user_id, u.username, p.name, p.id AS profile_id, c.created_at
            FROM connection_requests c
            JOIN users u ON u.id = c.to_user_id
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE c.from_user_id = ?
            ORDER BY c.created_at DESC, c.id DESC""",
        (g.user["id"],),
    ).fetchall()
    return jsonify([_person(r) for r in rows]), 200

@interest_bp.get("/received")
@login_required
def received():
    """People who showed interest in me."""
    rows = get_db().execute(
        """SELECT u.id AS user_id, u.username, p.name, p.id AS profile_id, c.created_at
            FROM connection_requests c
            JOIN users u ON u.id = c.from_user_id
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE c.to_user_id = ?
            ORDER BY c.created_at DESC, c.id DESC""",
        (g.user["id"],),
    ).fetchall()
    return jsonify([_person(r) for r in rows]), 200

@interest_bp.get("/mutual")
@login_required
def mutual():
    """People where interest goes both ways: I sent one AND they sent one back."""
    rows = get_db().execute(
        """SELECT u.id AS user_id, u.username, p.name, p.id AS profile_id,
            MAX(mine.created_at, theirs.created_at) AS created_at
            FROM connection_requests mine
            JOIN connection_requests theirs
            ON theirs.from_user_id = mine.to_user_id
            AND theirs.to_user_id   = mine.from_user_id
            JOIN users u ON u.id = mine.to_user_id
            LEFT JOIN profiles p ON p.user_id = u.id
            WHERE mine.from_user_id = ?
            ORDER BY created_at DESC, u.id""",
        (g.user["id"],),
    ).fetchall()
    return jsonify([_person(r) for r in rows]), 200