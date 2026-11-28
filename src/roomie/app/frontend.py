"""Frontend pages using the existing backend session authentication."""

from flask import g, redirect, render_template, request, session, url_for

from .auth import MIN_PASSWORD_LENGTH
from .profile_state import HOUSING_LABELS, is_complete, profile_for_user, safe_destination

PREFERENCE_FIELDS = {
    'cleanliness': {'label': 'Cleanliness', 'choices': {
        'relaxed': 'Relaxed', 'moderate': 'Moderate', 'very_clean': 'Very clean'}},
    'sleep_schedule': {'label': 'Sleep schedule', 'choices': {
        'early': 'Early sleeper', 'late': 'Night owl', 'flexible': 'Flexible'}},
    'study_habits': {'label': 'Study environment', 'choices': {
        'quiet': 'Quiet', 'social': 'Social', 'mixed': 'A mix of both'}},
    'smoking_preference': {'label': 'Smoking', 'choices': {
        'non_smoking': 'Non-smoking', 'smoking_ok': 'Smoking is okay'}},
    'pet_preference': {'label': 'Pets', 'choices': {
        'no_pets': 'No pets', 'pets_ok': 'Pets are okay'}},
}
PREFERENCE_SECTIONS = (
    ('Daily rhythm', ('cleanliness', 'sleep_schedule', 'study_habits')),
    ('Shared space', ('smoking_preference', 'pet_preference')),
)


def register_pages(app):
    def read_api(endpoint, **values):
        # Reuse the exact registered JSON GET handler in this request, including
        # its authentication, validation, SQL, and ranking. No internal HTTP
        # request, second matching algorithm, or separate database is needed.
        response = app.make_response(app.view_functions[endpoint](**values))
        return response.get_json(), response.status_code

    @app.get("/")
    def home():
        featured = []
        if g.user is not None:
            data, status = read_api("matches.find_matches")
            if status == 200:
                featured = data[:3]
        return render_template("home.html", featured_profiles=featured)

    @app.context_processor
    def authentication_context():
        own = profile_for_user(g.user['id']) if g.user is not None else None
        account_name = (own['name'].strip() if own and own['name'].strip() else g.user['username']) if g.user else None
        return {"nav_user": g.user, "account_name": account_name, "auth_enabled": True,
                "housing_labels": HOUSING_LABELS, "logout_endpoint": "auth.logout",
                "min_password_length": MIN_PASSWORD_LENGTH}

    @app.get("/login")
    def login():
        return render_template("login.html")

    @app.get("/register")
    def register():
        return render_template("register.html")

    def personal_profile():
        data, status = read_api("profiles.get_my_profile")
        return data if status == 200 else None

    @app.get("/profile")
    def profile():
        if g.user is None:
            return redirect(url_for('login', next=request.path))
        saved = personal_profile()
        if not is_complete(saved):
            return redirect(url_for('profile_setup'))
        intended = safe_destination(session.pop('profile_next', None))
        if intended and intended != '/profile':
            return redirect(intended)
        return render_template('profile.html', profile=saved)

    @app.get("/profile/setup")
    def profile_setup():
        if g.user is None:
            return redirect(url_for('login', next=request.path))
        saved = personal_profile()
        if is_complete(saved):
            return redirect(url_for('profile'))
        return render_template('profile_form.html', saved=saved or {}, mode='setup')

    @app.get("/profile/edit")
    def profile_edit():
        if g.user is None:
            return redirect(url_for('login', next=request.path))
        saved = personal_profile()
        if not is_complete(saved):
            return redirect(url_for('profile_setup'))
        return render_template('profile_form.html', saved=saved, mode='edit')

    @app.get("/preferences")
    def preferences():
        if g.user is None:
            return redirect(url_for('login', next=request.path))
        return preferences_page('preferences.html')

    def preferences_page(template):
        # Reuse the GET API handler, retaining Python's full SQLite integer range.
        saved, status = read_api('preferences.get_preferences')
        error = saved.get('error', 'Unable to load your preferences.') if status != 200 else None
        return render_template(template, saved=saved if status == 200 else {},
                               preferences_error=error, preference_fields=PREFERENCE_FIELDS,
                               preference_sections=PREFERENCE_SECTIONS,
                               preferences_empty=status == 200 and all(saved.get(key) is None
                                   for key in (*PREFERENCE_FIELDS, 'budget'))), status

    @app.get("/preferences/edit")
    def preferences_edit():
        if g.user is None:
            # Retain the existing safe post-login destination and auth rules.
            return redirect(url_for('login', next=url_for('preferences')))
        return preferences_page('preferences_form.html')

    @app.get("/find-roommates", endpoint="matches")
    def matches_page():
        if g.user is None:
            return redirect(url_for("login"))
        # A comma-separated form control becomes the API's repeated interest
        # parameters via a normal GET redirect, including without JavaScript.
        if "interests" in request.args:
            args = request.args.copy()
            interests = args.poplist("interests")
            values = args.getlist("interest") + [
                part.strip() for value in interests for part in value.split(",") if part.strip()
            ]
            args.setlist("interest", values)
            return redirect(url_for("matches", **args.to_dict(flat=False)))
        data, status = read_api("matches.find_matches")
        return render_template("matches.html", matches=data if status == 200 else [],
                               match_error=data.get("error") if status != 200 else None), status

    @app.get("/my-matches")
    def my_matches():
        if g.user is None:
            return redirect(url_for('login', next=url_for('my_matches')))
        return render_template('my_matches.html')

    @app.get("/roommate/<int:profile_id>", endpoint="profile_detail")
    def roommate_page(profile_id):
        if g.user is None:
            return redirect(url_for("login"))
        data, status = read_api("profiles.get_profile", profile_id=profile_id)
        lifestyle = None
        lifestyle_error = None
        if status == 200:
            lifestyle, preference_status = read_api('preferences.get_profile_preferences', profile_id=profile_id)
            if preference_status != 200:
                lifestyle = None
                lifestyle_error = 'Lifestyle preferences could not be loaded.'
        return render_template("profile_detail.html", profile=data if status == 200 else None,
                               profile_error=data.get("error") if status != 200 else None,
                               lifestyle=lifestyle, lifestyle_error=lifestyle_error,
                               preference_fields=PREFERENCE_FIELDS), status
