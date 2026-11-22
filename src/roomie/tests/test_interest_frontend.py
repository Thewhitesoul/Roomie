"""Interest UI contracts and real API state with separate session cookie jars."""
import pytest
from flask.testing import FlaskClient

from app import create_app


def headers(client):
    return {'X-CSRF-Token': client.get('/auth/csrf').json['csrf_token']}


def account(app, username, with_profile=True):
    client = FlaskClient(app, app.response_class)
    response = client.post('/auth/register', json={
        'username': username, 'email': f'{username}@washburn.edu', 'password': 'password123',
    }, headers=headers(client))
    assert response.status_code == 201
    user = response.json['user']
    profile = None
    if with_profile:
        response = client.post('/profiles', json={
            'name': username.title(), 'age': 24, 'preferred_location': 'Topeka',
            'housing_status': 'needs_housing', 'interests': ['cooking'],
        }, headers=headers(client))
        assert response.status_code == 201
        profile = response.json
    return client, user, profile


@pytest.fixture
def pair(app):
    account(app, 'padding', with_profile=False)
    return account(app, 'alice'), account(app, 'bob')


def change(client, method, uid, **body):
    return client.open(f'/interest/{uid}', method=method, json=body, headers=headers(client))


def test_detail_user_id_and_my_matches_navigation(pair):
    (alice, _, own), (_, bob_user, bob_profile) = pair
    assert bob_user['id'] != bob_profile['id']
    response = alice.get(f'/roommate/{bob_profile["id"]}')
    assert response.status_code == 200
    for text in ('data-interest-panel', f'data-user-id="{bob_user["id"]}"',
                 f'data-action-url="/interest/{bob_user["id"]}"',
                 'data-sent-url="/interest/sent"', 'data-mutual-url="/interest/mutual"',
                 'data-interest-action="send"', 'Show Interest', '/static/interests.js',
                 'href="/my-matches"'):
        assert text in response.text
    assert 'coming soon' not in response.text
    nav = response.text.split('<nav', 1)[1].split('</nav>', 1)[0]
    assert 'href="/my-matches"' in nav
    own_page = alice.get(f'/roommate/{own["id"]}')
    assert 'data-interest-panel' not in own_page.text
    assert 'This is your profile.' in own_page.text
    # Merely rendering a page never sends an interest.
    assert alice.get('/interest/sent').json == []


def test_my_matches_is_get_only_and_serves_script(pair):
    client = pair[0][0]
    response = client.get('/my-matches')
    assert response.status_code == 200
    for text in ('Mutual Matches', 'Interests Sent', 'Interests Received', 'Loading your connections',
                 'data-received-url="/interest/received"', 'data-profile-url="/roommate/0"'):
        assert text in response.text
    assert response.headers['Cache-Control'] == 'no-store'
    assert client.post('/my-matches', json={}, headers=headers(client)).status_code == 405
    asset = client.get('/static/interests.js')
    assert asset.status_code == 200 and b'X-CSRF-Token' in asset.data


def test_sent_received_and_duplicate_are_real_records(pair):
    (alice, alice_user, alice_profile), (bob, bob_user, bob_profile) = pair
    sent = change(alice, 'POST', bob_user['id'])
    assert sent.status_code == 201
    assert sent.json == {'to_user_id': bob_user['id'], 'mutual': False}
    assert alice.get('/interest/mutual').json == []
    assert bob.get('/interest/mutual').json == []
    assert change(alice, 'POST', bob_user['id']).status_code == 409
    records = alice.get('/interest/sent').json
    assert len(records) == 1
    assert records[0]['profile_id'] == bob_profile['id']
    assert records[0]['user_id'] == bob_user['id']
    assert records[0]['name'] == 'Bob' and records[0]['username'] == 'bob'
    assert records[0]['since']
    received = bob.get('/interest/received').json
    assert received[0]['profile_id'] == alice_profile['id']
    assert received[0]['user_id'] == alice_user['id']
    assert set(received[0]) == {'user_id', 'username', 'name', 'profile_id', 'since'}


def test_mutual_then_withdraw_updates_both_users(pair):
    (alice, alice_user, _), (bob, bob_user, _) = pair
    change(alice, 'POST', bob_user['id'])
    response = change(bob, 'POST', alice_user['id'])
    assert response.status_code == 201 and response.json['mutual'] is True
    assert alice.get('/interest/mutual').json[0]['user_id'] == bob_user['id']
    assert bob.get('/interest/mutual').json[0]['user_id'] == alice_user['id']
    assert change(alice, 'DELETE', bob_user['id']).status_code == 200
    assert alice.get('/interest/sent').json == []
    assert bob.get('/interest/received').json == []
    assert alice.get('/interest/mutual').json == []
    assert bob.get('/interest/mutual').json == []
    # Withdrawal never removes the other user's incoming interest.
    assert alice.get('/interest/received').json[0]['user_id'] == bob_user['id']
    assert change(alice, 'DELETE', bob_user['id']).status_code == 404


def test_invalid_and_self_ids(pair):
    alice, own, _ = pair[0]
    assert change(alice, 'POST', own['id']).status_code == 400
    assert change(alice, 'POST', 999999).status_code == 404
    assert change(alice, 'DELETE', 999999).status_code == 404
    assert alice.get('/interest/sent').json == []
    assert alice.post('/interest/not-an-id', json={}, headers=headers(alice)).status_code == 404


@pytest.mark.parametrize('path', ['/interest/sent', '/interest/received', '/interest/mutual'])
def test_anonymous_read_access(app, path):
    client = FlaskClient(app, app.response_class)
    assert client.get(path).status_code == 401
    response = client.get('/my-matches?logged_in=true')
    assert response.status_code == 302 and response.location == '/login?next=/my-matches'


@pytest.mark.parametrize('method', ['POST', 'DELETE'])
def test_anonymous_mutation_access(app, method):
    client = FlaskClient(app, app.response_class)
    assert change(client, method, 1).status_code == 401


@pytest.mark.parametrize('method', ['POST', 'DELETE'])
def test_csrf_missing_wrong_and_cross_session(pair, method):
    (alice, _, _), (bob, bob_user, _) = pair
    if method == 'DELETE':
        change(alice, 'POST', bob_user['id'])
    for bad_headers in ({}, {'X-CSRF-Token': 'wrong'}, headers(bob)):
        response = alice.open(f'/interest/{bob_user["id"]}', method=method, json={}, headers=bad_headers)
        assert response.status_code == 403
    assert len(alice.get('/interest/sent').json) == (1 if method == 'DELETE' else 0)


def test_account_isolation_and_sender_body_is_ignored(app, pair):
    (alice, alice_user, _), (bob, bob_user, _) = pair
    charlie, charlie_user, _ = account(app, 'charlie')
    change(alice, 'POST', bob_user['id'])
    assert charlie.get('/interest/sent').json == []
    assert charlie.get('/interest/received').json == []
    assert change(charlie, 'DELETE', bob_user['id']).status_code == 404
    assert len(alice.get('/interest/sent').json) == 1
    assert change(charlie, 'POST', bob_user['id'], from_user_id=alice_user['id']).status_code == 201
    assert {p['user_id'] for p in bob.get('/interest/received').json} == {alice_user['id'], charlie_user['id']}


def test_users_without_profiles_and_private_fields(app, pair):
    alice, _, _ = pair[0]
    reader, user, _ = account(app, 'without_profile', with_profile=False)
    assert change(alice, 'POST', user['id']).status_code == 201
    person = alice.get('/interest/sent').json[0]
    assert person['name'] is None and person['profile_id'] is None
    assert person['username'] == 'without_profile'
    assert 'email' not in person and 'password_hash' not in person
    assert reader.get('/my-matches').status_code == 200


def test_state_persists_through_fresh_flask_app(app, pair):
    (alice, alice_user, _), (bob, bob_user, _) = pair
    change(alice, 'POST', bob_user['id'])
    change(bob, 'POST', alice_user['id'])
    sent = alice.get('/interest/sent').json
    mutual = alice.get('/interest/mutual').json
    fresh = create_app({'TESTING': True, 'DATABASE': app.config['DATABASE'], 'SECRET_KEY': 'fresh-interest-test'})
    client = fresh.test_client()
    assert client.get('/interest/sent').status_code == 401
    response = client.post('/auth/login', json={'email': 'alice@washburn.edu', 'password': 'password123'}, headers=headers(client))
    assert response.status_code == 200
    assert client.get('/interest/sent').json == sent
    assert client.get('/interest/mutual').json == mutual
    assert client.get('/my-matches').status_code == 200


def test_safe_login_return_to_my_matches(pair):
    alice = pair[0][0]
    alice.post('/auth/logout', json={}, headers=headers(alice))
    response = alice.post('/auth/login', json={
        'email': 'alice@washburn.edu', 'password': 'password123', 'next': '/my-matches',
    }, headers=headers(alice))
    assert response.json['redirect'] == '/my-matches'
