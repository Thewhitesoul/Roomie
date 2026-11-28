"""Profile page/API integration; existing SQL and authentication remain authoritative."""
import pytest
from flask.testing import FlaskClient

from app import create_app


def csrf(client):
    return {'X-CSRF-Token': client.get('/auth/csrf').json['csrf_token']}


def signup(client, username='profile_user'):
    response = client.post('/auth/register', json={
        'username': username, 'email': f'{username}@washburn.edu', 'password': 'password123',
    }, headers=csrf(client))
    assert response.status_code == 201
    return response.json['user']['id']


def profile(**changes):
    return {'name': 'Arpan', 'age': 21, 'housing_status': 'needs_housing', 'preferred_location': 'Topeka',
            'bio': 'Looking for a quiet home.', 'interests': ['cooking', 'hiking'], **changes}


def test_profile_page_contract(client):
    signup(client)
    assert client.get('/profile').location == '/profile/setup'
    response = client.get('/profile/setup')
    assert response.status_code == 200
    for text in ('data-profile-form', 'data-read-url="/profiles/me"',
                 'data-create-url="/profiles"', 'data-update-url="/profiles/me"',
                 'maxlength="60"', 'name="preferred_location"', 'name="bio"',
                 'name="interests"', 'Save and continue', 'account-dropdown'):
        assert text in response.text
    for text in ('data-preview-form',):
        assert text not in response.text


def test_create_read_update_same_profile(client):
    uid = signup(client)
    assert client.get('/profiles/me').status_code == 404
    response = client.post('/profiles', json=profile())
    assert response.status_code == 201
    saved = response.json
    assert saved['user_id'] == uid
    assert client.get('/profiles/me').json == saved
    response = client.put('/profiles/me', json=profile(name='Updated', interests=[]))
    assert response.status_code == 200
    assert response.json['id'] == saved['id']
    assert response.json['name'] == 'Updated'
    assert response.json['interests'] == []
    assert client.get('/profiles/me').json == response.json
    assert len(client.get('/profiles').json) == 1


@pytest.mark.parametrize('bad_fields', [
    {'name': ''}, {'name': '  '}, {'name': 'n' * 61},
    {'preferred_location': 'l' * 101}, {'bio': 'b' * 501},
    {'interests': ['x'] * 11}, {'interests': ['x' * 31]},
    {'interests': ['  ']}, {'interests': [7]},
])
@pytest.mark.parametrize('existing', [False, True])
def test_invalid_input_does_not_save_or_overwrite(client, bad_fields, existing):
    signup(client)
    if existing:
        assert client.post('/profiles', json=profile()).status_code == 201
    path, method = ('/profiles/me', client.put) if existing else ('/profiles', client.post)
    response = method(path, json=profile(**bad_fields))
    assert response.status_code == 400
    assert response.json['error']
    if existing:
        assert client.get('/profiles/me').json['name'] == 'Arpan'
        assert client.get('/profiles/me').json['interests'] == ['cooking', 'hiking']
    else:
        assert client.get('/profiles/me').status_code == 404


def test_profile_api_limits_and_budget_preserved(client):
    signup(client)
    fields = profile(name='n' * 60, preferred_location='l' * 100,
                     bio='b' * 500, interests=[str(i) + 'i' * 29 for i in range(10)])
    assert client.post('/profiles', json={**fields, 'budget': 700}).status_code == 201
    response = client.put('/profiles/me', json=profile())
    assert response.status_code == 200
    assert response.json['budget'] == 700  # The UI doesn't edit this existing API field.


def test_anonymous_profile_access(client):
    response = client.get('/profile?user_id=1&logged_in=true')
    assert response.status_code == 302
    assert response.location == '/login?next=/profile'
    assert client.get('/profiles/me').status_code == 401
    assert client.post('/profiles', json=profile()).status_code == 401
    assert client.put('/profiles/me', json=profile()).status_code == 401


def test_profile_mutations_require_csrf(app):
    client = FlaskClient(app, app.response_class)
    signup(client)
    assert client.post('/profiles', json=profile()).status_code == 403
    assert client.post('/profiles', json=profile(), headers=csrf(client)).status_code == 201
    assert client.put('/profiles/me', json=profile(name='Wrong'),
                      headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    assert client.get('/profiles/me').json['name'] == 'Arpan'


def test_users_read_and_update_only_their_own_profile(app):
    alice, bob = (FlaskClient(app, app.response_class) for _ in range(2))
    signup(alice, 'alice')
    signup(bob, 'bob')
    assert alice.post('/profiles', json=profile(name='Alice'), headers=csrf(alice)).status_code == 201
    assert bob.get('/profiles/me').status_code == 404
    assert bob.put('/profiles/me', json=profile(name='Bob'), headers=csrf(bob)).status_code == 404
    assert alice.get('/profiles/me').json['name'] == 'Alice'


def test_profile_persists_in_fresh_flask_app(app, client):
    signup(client)
    assert client.post('/profiles', json=profile()).status_code == 201
    assert client.put('/profiles/me', json=profile(name='Persisted')).status_code == 200
    saved = client.get('/profiles/me').json
    # Fresh app, fresh cookie jar, same SQLite file; never reinitialize the database.
    restarted = create_app({'TESTING': True, 'SECRET_KEY': 'restart-test',
                            'DATABASE': app.config['DATABASE']})
    fresh = restarted.test_client()
    assert fresh.get('/profiles/me').status_code == 401
    response = fresh.post('/auth/login', json={
        'email': 'profile_user@washburn.edu', 'password': 'password123',
    }, headers=csrf(fresh))
    assert response.status_code == 200
    assert response.json['redirect'] == '/profile'
    assert fresh.get('/profile').status_code == 200
    assert fresh.get('/profiles/me').json == saved
