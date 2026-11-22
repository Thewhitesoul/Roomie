"""Session-bound CSRF protection for cookie-authenticated browser requests."""
import secrets

from flask import jsonify, request, session


def csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def init_app(app):
    app.jinja_env.globals["csrf_token"] = csrf_token

    @app.before_request
    def protect_mutations():
        if request.endpoint is None or request.method in {"GET", "HEAD", "OPTIONS"}:
            return
        expected = session.get("csrf_token")
        supplied = request.headers.get("X-CSRF-Token", "")
        if not (isinstance(expected, str) and supplied
                and secrets.compare_digest(expected.encode(), supplied.encode())):
            return jsonify(error="Your security token is missing or expired. Reload the page and try again."), 403

    @app.after_request
    def prevent_sensitive_caching(response):
        if response.mimetype in {"text/html", "application/json"}:
            response.headers["Cache-Control"] = "no-store"
        return response
