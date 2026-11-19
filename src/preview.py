from functools import wraps

from flask import Flask, render_template, abort, g, redirect, request, url_for

app = Flask(__name__)


def authenticated_user():
    # Backend integration point: load a verified user from the server session
    # into g.current_user before dispatch. The preview never authenticates users.
    user = g.get("current_user")
    return user if user is not None and user.is_authenticated else None


@app.context_processor
def authentication_context():
    return {"nav_user": authenticated_user()}


def login_required(view):
    @wraps(view)
    def protected(*args, **kwargs):
        if authenticated_user() is None:
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return protected


@app.route("/")
def home():
    return render_template("home.html", featured_profiles=sample_profiles)

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")

@app.route("/preferences")
@login_required
def preferences():
    return render_template("preferences.html")

sample_profiles = [
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


@app.route("/matches")
def matches():
    return render_template("matches.html", matches=sample_profiles)


@app.route("/profiles/<int:user_id>")
def profile_detail(user_id):
    person = next(
        (p for p in sample_profiles if p["user_id"] == user_id),
        None
    )

    if person is None:
        abort(404)

    return render_template("profile_detail.html", profile=person)
