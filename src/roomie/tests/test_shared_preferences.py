"""Only six lifestyle fields are shareable, read-only, through a profile ID."""
import pytest
from flask import jsonify
from flask.testing import FlaskClient

from app.db import get_db
from app.preferences import FIELDS


SETTINGS = {
    'cleanliness': 'very_clean', 'sleep_schedule': 'late', 'study_habits': 'mixed',
    'smoking_preference': 'non_smoking', 'pet_preference': 'pets_ok', 'budget': 950,
}


def headers(client):
    return {'X-CSRF-Token': client.get('/auth/csrf').json['csrf_token']}


def account(app, name, with_profile=True):
    client = FlaskClient(app, app.response_class)
    response = client.post('/auth/register', json={
        'username': name, 'email': f'{name}@washburn.edu', 'password': 'password123',
    }, headers=headers(client))
    assert response.status_code == 201
    user = response.json['user']
    profile = None
    if with_profile:
        response = client.post('/profiles', json={
            'name': name.title(), 'age': 24, 'preferred_location': 'Topeka',
            'housing_status': 'needs_housing', 'interests': ['cooking'], 'budget': 600,
        }, headers=headers(client))
        assert response.status_code == 201
        profile = response.json
    return client, user, profile


@pytest.fixture
def pair(app):
    account(app, 'shared_padding', with_profile=False)
    return account(app, 'shared_viewer'), account(app, 'shared_owner')


def save(client, values):
    response = client.put('/preferences/me', json=values, headers=headers(client))
    assert response.status_code == 200
    return response.json


def section(client, profile):
    text = client.get(f'/roommate/{profile["id"]}').text
    return text.split('data-roommate-preferences', 1)[1].split('</section>', 1)[0]


def test_profile_id_resolves_target_and_returns_only_six_fields(pair):
    (viewer, _, _), (owner, user, profile) = pair
    assert user['id'] != profile['id']
    save(viewer, {'cleanliness': 'relaxed', 'budget': 123})
    save(owner, SETTINGS)
    response = viewer.get(f'/preferences/profile/{profile["id"]}?user_id=2&profile_id=1')
    assert response.status_code == 200
    assert response.json == SETTINGS
    assert set(response.json) == set(FIELDS)
    assert response.headers['Cache-Control'] == 'no-store'
    for private in ('user_id', 'profile_id', 'email', 'username', 'password', 'password_hash', 'csrf_token', 'session'):
        assert private not in response.json
    assert 'shared_owner@washburn.edu' not in response.text
    assert viewer.get('/preferences/me').json['budget'] == 123
    assert owner.get('/preferences/me').json['budget'] == 950


def test_roommate_values_are_below_interests_in_existing_card_and_never_use_me(app, pair, monkeypatch):
    (viewer, _, _), (owner, _, profile) = pair
    save(owner, SETTINGS)
    def forbidden():
        pytest.fail('Roommate preferences must not read the viewer-owned /me endpoint')
    monkeypatch.setitem(app.view_functions, 'preferences.get_preferences', forbidden)
    response = viewer.get(f'/roommate/{profile["id"]}')
    assert response.status_code == 200
    assert response.text.index('<h2>Interests</h2>') < response.text.index('data-roommate-preferences') < response.text.index('data-interest-panel')
    lifestyle = section(viewer, profile)
    for label in ('Lifestyle preferences', 'Cleanliness', 'Very clean', 'Sleep schedule',
                  'Night owl', 'Study environment', 'A mix of both', 'Smoking preference',
                  'Non-smoking', 'Pet preference', 'Pets are okay', 'Monthly housing budget', '$950/month'):
        assert label in lifestyle
    assert 'preferences/edit' not in lifestyle
    assert '<form' not in lifestyle
    assert '<input' not in lifestyle
    assert '<button' not in lifestyle
    assert 'shared_owner@washburn.edu' not in response.text
    assert 'Cache-Control' in response.headers and response.headers['Cache-Control'] == 'no-store'


def test_missing_preferences_are_null_without_creating_a_row_or_using_profile_budget(app, pair):
    (viewer, _, _), (_, _, profile) = pair
    save(viewer, SETTINGS)
    assert viewer.get(f'/preferences/profile/{profile["id"]}').json == dict.fromkeys(FIELDS)
    lifestyle = section(viewer, profile)
    assert lifestyle.count('Not specified') == 6
    assert '$600/month' not in lifestyle  # Separate profile budget must not fill this gap.
    assert '$950/month' not in lifestyle  # Nor may the viewer's own preferences.
    with app.app_context():
        assert get_db().execute('SELECT COUNT(*) FROM preferences WHERE user_id=?', (profile['user_id'],)).fetchone()[0] == 0


def test_saved_changes_and_null_clearing_are_visible_to_the_other_account(pair):
    (viewer, _, _), (owner, _, profile) = pair
    save(owner, SETTINGS)
    save(owner, {'budget': 0, 'sleep_schedule': 'early'})
    assert '$0/month' in section(viewer, profile)
    assert 'Early sleeper' in section(viewer, profile)
    assert viewer.get(f'/preferences/profile/{profile["id"]}').json == {**SETTINGS, 'budget': 0, 'sleep_schedule': 'early'}
    save(owner, dict.fromkeys(FIELDS))
    assert section(viewer, profile).count('Not specified') == 6


def test_anonymous_access_and_spoofed_identifiers_do_not_authorize(app, pair):
    _, (owner, user, profile) = pair
    save(owner, SETTINGS)
    guest = FlaskClient(app, app.response_class)
    response = guest.get(f'/preferences/profile/{profile["id"]}?user_id={user["id"]}&logged_in=true')
    assert response.status_code == 401
    assert 'very_clean' not in response.text
    assert guest.get(f'/roommate/{profile["id"]}').location == '/login'


@pytest.mark.parametrize('method', ['POST', 'PUT', 'PATCH', 'DELETE'])
def test_shareable_route_never_allows_writing(pair, method):
    (viewer, _, _), (owner, _, profile) = pair
    save(owner, SETTINGS)
    response = viewer.open(f'/preferences/profile/{profile["id"]}', method=method,
                           json={'budget': 5}, headers=headers(viewer))
    assert response.status_code == 405
    assert owner.get('/preferences/me').json['budget'] == 950
    assert viewer.get('/preferences/me').json['budget'] is None


def test_ownership_and_csrf_on_me_remain_intact(pair):
    (viewer, _, _), (owner, user, profile) = pair
    save(owner, SETTINGS)
    assert viewer.put('/preferences/me', json={'user_id': user['id'], 'budget': 5}, headers=headers(viewer)).status_code == 400
    for supplied in ({}, {'X-CSRF-Token': 'invalid'}, headers(owner)):
        assert viewer.put('/preferences/me', json={'budget': 5}, headers=supplied).status_code == 403
    assert viewer.get(f'/preferences/profile/{profile["id"]}').json == SETTINGS


@pytest.mark.parametrize('identifier', ['0', '999999', '-1', 'not-an-id'])
def test_unknown_profiles_return_404(pair, identifier):
    viewer = pair[0][0]
    assert viewer.get(f'/preferences/profile/{identifier}').status_code == 404


def test_preferences_without_a_profile_do_not_become_addressable_by_user_id(app, pair):
    viewer = pair[0][0]
    owner, user, _ = account(app, 'shared_no_profile', with_profile=False)
    save(owner, SETTINGS)
    assert viewer.get(f'/preferences/profile/{user["id"]}').status_code == 404


def test_free_text_is_escaped_and_large_budgets_retain_precision(pair):
    (viewer, _, _), (owner, _, profile) = pair
    hostile = '<img src=x onerror=window.pwned=1>'
    save(owner, {'cleanliness': hostile, 'budget': 9223372036854775807})
    lifestyle = section(viewer, profile)
    assert hostile not in lifestyle
    assert '&lt;img' in lifestyle
    assert '$9223372036854775807/month' in lifestyle
    assert viewer.get(f'/preferences/profile/{profile["id"]}').json['cleanliness'] == hostile


def test_editor_discloses_visibility_before_the_form(pair):
    editor = pair[0][0].get('/preferences/edit').text
    assert 'visible to other logged-in Roomie users on your roommate profile.' in editor
    assert editor.index('id="preferences-visibility"') < editor.index('data-preferences-form')
    assert 'aria-describedby="preferences-visibility"' in editor


def test_preference_api_failure_is_not_presented_as_unset_or_breaking_interest(app, pair, monkeypatch):
    (viewer, _, _), (_, _, profile) = pair
    def unavailable(profile_id):
        return jsonify(error='Temporary preferences failure.'), 503
    monkeypatch.setitem(app.view_functions, 'preferences.get_profile_preferences', unavailable)
    response = viewer.get(f'/roommate/{profile["id"]}')
    assert response.status_code == 200
    assert 'Lifestyle preferences could not be loaded.' in response.text
    assert 'Not specified' not in section(viewer, profile)
    assert 'data-interest-panel' in response.text
