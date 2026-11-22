"""Real preferences API, protected HTML views, security, and SQLite persistence."""
from html.parser import HTMLParser

import pytest
from flask import jsonify
from flask.testing import FlaskClient

from app import create_app
from app.db import get_db
from app.frontend import PREFERENCE_FIELDS


def headers(client):
    return {'X-CSRF-Token': client.get('/auth/csrf').json['csrf_token']}


def save(client, data):
    return client.put('/preferences/me', json=data, headers=headers(client))


def account(app, username):
    client = FlaskClient(app, app.response_class)
    response = client.post('/auth/register', json={
        'username': username, 'email': f'{username}@washburn.edu', 'password': 'password123',
    }, headers=headers(client))
    assert response.status_code == 201
    uid = response.json['user']['id']
    response = client.post('/profiles', json={
        'name': username.title(), 'age': 25, 'housing_status': 'needs_housing',
        'preferred_location': 'Topeka', 'interests': ['music'], 'budget': 875,
    }, headers=headers(client))
    assert response.status_code == 201
    return client, uid


@pytest.fixture
def pair(app):
    return account(app, 'preferences_owner'), account(app, 'preferences_other')


ALL_FIELDS = {
    'cleanliness': 'very_clean', 'sleep_schedule': 'late', 'study_habits': 'mixed',
    'smoking_preference': 'non_smoking', 'pet_preference': 'pets_ok', 'budget': 950,
}


class Page(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def test_initial_state_has_null_values_and_gets_never_create_a_row(app, pair):
    client, uid = pair[0]
    assert client.get('/preferences/me').json == {'user_id': uid, **dict.fromkeys(ALL_FIELDS)}
    response = client.get('/preferences')
    assert response.status_code == 200
    page = Page(response.text)
    assert sum('profile-content' in attrs.get('class', '').split() for _, attrs in page.tags) == 1
    assert sum(attrs.get('href') == '/preferences/edit' for _, attrs in page.tags) == 1
    assert 'data-preview-form' not in response.text
    assert 'data-preferences-form' not in response.text
    for name in ('Relaxed', 'Moderate', 'Very clean', 'Early sleeper', 'Night owl',
                 'Flexible', 'Quiet', 'Social', 'A mix of both', 'Non-smoking',
                 'Smoking is okay', 'No pets', 'Pets are okay', 'No preference'):
        assert name in response.text
    assert client.get('/preferences/edit').status_code == 200
    with app.app_context():
        assert get_db().execute('SELECT * FROM preferences').fetchall() == []


def test_six_fields_saved_displayed_and_prefilled_without_changing_profile_or_matching(pair):
    client, uid = pair[0]
    profile = client.get('/profiles/me').json
    matches = client.get('/matches').json
    assert save(client, ALL_FIELDS).json == {'user_id': uid, **ALL_FIELDS}
    assert client.get('/preferences/me').json == {'user_id': uid, **ALL_FIELDS}
    view = client.get('/preferences')
    assert 'Preferences saved.' in view.text
    for field, info in PREFERENCE_FIELDS.items():
        assert info['choices'][ALL_FIELDS[field]] in view.text
    assert '$950/month' in view.text
    assert 'Choices:' not in view.text
    editor = client.get('/preferences/edit')
    for field in PREFERENCE_FIELDS:
        assert f'value="{ALL_FIELDS[field]}" selected' in editor.text
    assert 'value="950"' in editor.text
    assert 'action="/preferences/me"' in editor.text
    assert '/static/preferences.js' in editor.text
    assert client.get('/static/preferences.js').status_code == 200
    assert client.get('/profiles/me').json == profile
    assert client.get('/matches').json == matches


def test_updates_clear_nulls_and_cancel_destinations_do_not_save(pair):
    client, uid = pair[0]
    save(client, ALL_FIELDS)
    assert save(client, {'budget': 0, 'sleep_schedule': None}).json == {
        'user_id': uid, **ALL_FIELDS, 'budget': 0, 'sleep_schedule': None,
    }
    before = client.get('/preferences/me').json
    # Visiting the editor and its Cancel destination never issues a PUT.
    editor = client.get('/preferences/edit')
    assert 'href="/preferences">Cancel' in editor.text
    assert client.get('/preferences').status_code == 200
    assert client.get('/preferences/me').json == before
    assert save(client, dict.fromkeys(ALL_FIELDS)).json == {'user_id': uid, **dict.fromkeys(ALL_FIELDS)}
    assert 'No budget set' in client.get('/preferences').text


@pytest.mark.parametrize('field', list(PREFERENCE_FIELDS))
def test_free_text_contract_trim_null_and_safe_legacy_prefill(pair, field):
    client, _ = pair[0]
    legacy = '<img src=x onerror=window.pwned=1>'
    assert save(client, {field: f'  {legacy}  '}).json[field] == legacy
    for path in ('/preferences', '/preferences/edit'):
        text = client.get(path).text
        assert legacy not in text
        assert '&lt;img' in text
    assert '(saved value)</option>' in client.get('/preferences/edit').text
    assert save(client, {field: 'é' * 100}).status_code == 200
    assert save(client, {field: 'é' * 101}).status_code == 400
    assert save(client, {field: None}).json[field] is None


@pytest.mark.parametrize('budget', [0, 1, 9223372036854775807])
def test_integer_boundaries_are_not_rounded_in_html(pair, budget):
    client, _ = pair[0]
    assert save(client, {'budget': budget}).json['budget'] == budget
    assert f'${budget}/month' in client.get('/preferences').text
    assert f'value="{budget}"' in client.get('/preferences/edit').text


@pytest.mark.parametrize('content_type,body', [
    ('application/json', '{'), ('application/json', 'null'),
    ('application/json', '[1]'), ('text/plain', '{}'),
    ('application/x-www-form-urlencoded', 'budget=500'),
])
def test_malformed_and_non_json_inputs_leave_saved_values_unchanged(pair, content_type, body):
    client, _ = pair[0]
    save(client, ALL_FIELDS)
    assert client.put('/preferences/me', data=body, content_type=content_type,
                      headers=headers(client)).status_code == 400
    assert {key: client.get('/preferences/me').json[key] for key in ALL_FIELDS} == ALL_FIELDS


@pytest.mark.parametrize('path', ['/preferences', '/preferences/edit', '/preferences/me'])
def test_authentication_and_read_only_pages(app, path):
    client = FlaskClient(app, app.response_class)
    response = client.get(path)
    if path == '/preferences/me':
        assert response.status_code == 401
        assert client.put(path, json={}, headers=headers(client)).status_code == 401
    else:
        assert response.status_code == 302
        assert response.location == '/login?next=/preferences'
        assert client.post(path, json={}, headers=headers(client)).status_code == 405


def test_csrf_and_account_isolation(pair):
    (owner, uid), (other, other_uid) = pair
    save(owner, ALL_FIELDS)
    for supplied in ({}, {'X-CSRF-Token': 'invalid'}, headers(other)):
        assert owner.put('/preferences/me', json={'budget': 5}, headers=supplied).status_code == 403
    assert owner.get('/preferences/me').json['budget'] == 950
    assert other.get(f'/preferences/me?user_id={uid}').json == {'user_id': other_uid, **dict.fromkeys(ALL_FIELDS)}
    for forbidden in ({'id': uid}, {'user_id': uid}, {'unknown': 'x'}):
        assert save(other, forbidden).status_code == 400
    assert save(other, {'budget': 12}).json['budget'] == 12
    assert owner.get('/preferences/me').json['budget'] == 950
    assert '$950/month' not in other.get('/preferences').text


def test_fresh_app_login_and_repeat_schema_init_preserve_all_records(app, pair):
    (owner, uid), (_, other_uid) = pair
    save(owner, ALL_FIELDS)
    assert owner.post(f'/interest/{other_uid}', json={}, headers=headers(owner)).status_code == 201
    with app.app_context():
        tables = ('users', 'profiles', 'profile_interests', 'connection_requests', 'preferences')
        before = {table: [tuple(row) for row in get_db().execute(f'SELECT * FROM {table}')] for table in tables}
    for _ in range(2):
        result = app.test_cli_runner().invoke(args=['init-db'])
        assert result.exit_code == 0, result.output
    fresh = create_app({'TESTING': True, 'SECRET_KEY': 'restart-preferences', 'DATABASE': app.config['DATABASE']})
    client = FlaskClient(fresh, fresh.response_class)
    assert client.post('/auth/login', json={'email': 'preferences_owner@washburn.edu',
        'password': 'password123'}, headers=headers(client)).status_code == 200
    assert client.get('/preferences/me').json == {'user_id': uid, **ALL_FIELDS}
    assert '$950/month' in client.get('/preferences').text
    with fresh.app_context():
        after = {table: [tuple(row) for row in get_db().execute(f'SELECT * FROM {table}')] for table in tables}
    assert after == before


@pytest.mark.parametrize('path', ['/preferences', '/preferences/edit'])
def test_pages_reuse_the_registered_get_api_and_never_allow_edit_after_read_error(app, pair, monkeypatch, path):
    client, _ = pair[0]
    def unavailable():
        return jsonify(error='Preferences are temporarily unavailable.'), 503
    monkeypatch.setitem(app.view_functions, 'preferences.get_preferences', unavailable)
    response = client.get(path)
    assert response.status_code == 503
    assert 'Preferences are temporarily unavailable.' in response.text
    assert 'Retry loading preferences' in response.text
    assert 'data-preferences-form' not in response.text
