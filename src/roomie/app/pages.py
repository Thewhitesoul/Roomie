from functools import wraps

from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for

pages_bp = Blueprint("pages", __name__)

# Fictional sample data from the old frontend preview. Replace with real queries in a later step.
SAMPLE_PROFILES = [
    {
        "user_id": 1,
        "name": "Alex",
        "age": 21,
        "location": "Topeka",
        "bio": "I enjoy cooking, quiet evenings, and soccer.",
        "interests": "Cooking, soccer, movies"
    },
    {
        "user_id": 2,
        "name": "Jordan",
        "age": 22,
        "location": "Lawrence",
        "bio": "Looking for a tidy roommate who enjoys music.",
        "interests": "Music, reading, gaming"
    },
    {
        "user_id": 3,
        "name": "Taylor",
        "age": 20,
        "location": "Topeka",
        "bio": "Early riser who enjoys hiking and studying at home.",
        "interests": "Hiking, fitness, coffee"
    }
]


def page_login_required(view):
    """For pages: send logged-out users to the login page.
    (auth.login_required returns a 401 JSON error, which is right for the API.)"""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("pages.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@pages_bp.app_context_processor
def nav_context():
    # auth.py loads g.user before every request
    return {"nav_user": g.get("user")}


@pages_bp.get("/")
def home():
    return render_template("home.html", featured_profiles=SAMPLE_PROFILES)

@pages_bp.get("/login")
def login():
    return render_template("login.html")

@pages_bp.get("/register")
def register():
    return render_template("register.html")

@pages_bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("pages.home"))

@pages_bp.get("/profile")
@page_login_required
def profile():
    return render_template("profile.html")

@pages_bp.get("/preferences")
@page_login_required
def preferences():
    return render_template("preferences.html")

@pages_bp.get("/matches")
def matches():
    return render_template("matches.html", matches=SAMPLE_PROFILES)

@pages_bp.get("/profiles/<int:user_id>")
def profile_detail(user_id):
    person = next((p for p in SAMPLE_PROFILES if p["user_id"] == user_id), None)
    if person is None:
        abort(404)
    return render_template("profile_detail.html", profile=person)
