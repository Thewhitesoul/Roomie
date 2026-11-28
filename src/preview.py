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
    return render_template("home.html", featured_profiles=[])

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

@app.route("/matches")
def matches():
    return render_template("matches.html", matches=[])


# The standalone visual preview has no real users or protected profile data.
@app.route("/roommate/<int:profile_id>")
def profile_detail(profile_id):
    abort(404)
