"""Notification wiring and session-scoped API records; UI counts run in Chrome."""
import pytest
from flask.testing import FlaskClient


def csrf(client):
    return {'X-CSRF-Token': client.get('/auth/csrf').json['csrf_token']}


def register(app, username):
    client = FlaskClient(app, app.response_class)
    response = client.post('/auth/register', json={
        'username': username, 'email': f'{username}@washburn.edu', 'password': 'password123',
    }, headers=csrf(client))
    assert response.status_code == 201
    return client, response.json['user']['id']


@pytest.mark.parametrize('path', ['/', '/login', '/register'])
def test_anonymous_navigation_has_no_private_notification_interface(app, path):
    response = app.test_client().get(path)
    assert response.status_code == 200
    assert 'data-notifications' not in response.text
    assert '/static/notifications.js' not in response.text
    assert 'data-match-announcement' not in response.text


@pytest.mark.parametrize('path', ['/', '/profile/setup', '/preferences', '/find-roommates', '/my-matches'])
def test_authenticated_notifications_are_wired_without_writing_records(app, path):
    client, _ = register(app, 'notification_reader')
    response = client.get(path)
    assert response.status_code == 200
    for contract in ('/static/notifications.js', 'data-notifications',
                     'aria-expanded="false" aria-controls="notification-panel"',
                     'data-sent-url="/interest/sent"', 'data-received-url="/interest/received"',
                     'data-mutual-url="/interest/mutual"', 'data-profile-url="/roommate/0"',
                     'Your connections', 'Interested in you', 'data-notification-badge hidden',
                     'aria-label="Refresh connections"'):
        assert contract in response.text
    panel = response.text.split('id="notification-panel"', 1)[1].split('</section>', 1)[0]
    assert 'href="/my-matches">Open My Matches' in panel
    assert 'Pending incoming interests' not in panel
    assert 'Pending means' not in panel
    assert 'notification-note' not in panel
    if path == '/my-matches':
        assert 'data-match-announcement' not in response.text  # Its own match banner stays intact.
        assert 'data-mutual-banner' in response.text
    else:
        assert 'data-match-announcement role="status" aria-live="polite" hidden' in response.text
    for kind in ('sent', 'received', 'mutual'):
        assert client.get(f'/interest/{kind}').json == []
    asset = client.get('/static/notifications.js')
    assert asset.status_code == 200 and asset.mimetype in ('text/javascript', 'application/javascript')
    assert response.headers['Cache-Control'] == 'no-store'


def test_notification_sources_follow_incoming_mutual_and_withdrawals(app):
    alice, aid = register(app, 'notification_alice')
    bob, bid = register(app, 'notification_bob')
    assert alice.post(f'/interest/{bid}', json={}, headers=csrf(alice)).status_code == 201
    assert bob.get('/interest/sent').json == []
    incoming = bob.get('/interest/received').json
    assert [p['user_id'] for p in incoming] == [aid]
    assert incoming[0]['profile_id'] is None
    assert incoming[0]['username'] == 'notification_alice'
    assert bob.get('/interest/mutual').json == []
    assert bob.post(f'/interest/{aid}', json={}, headers=csrf(bob)).json['mutual'] is True
    for client, other in ((alice, bid), (bob, aid)):
        assert [p['user_id'] for p in client.get('/interest/mutual').json] == [other]
    assert alice.delete(f'/interest/{bid}', json={}, headers=csrf(alice)).status_code == 200
    assert alice.get('/interest/mutual').json == bob.get('/interest/mutual').json == []
    assert bob.get('/interest/received').json == []
    assert [p['user_id'] for p in alice.get('/interest/received').json] == [bid]


@pytest.mark.parametrize('kind', ['sent', 'received', 'mutual'])
def test_notification_sources_require_session_and_ignore_foreign_account_query(app, kind):
    alice, aid = register(app, 'notification_owner')
    bob, bid = register(app, 'notification_peer')
    outsider, _ = register(app, 'notification_outsider')
    alice.post(f'/interest/{bid}', json={}, headers=csrf(alice))
    bob.post(f'/interest/{aid}', json={}, headers=csrf(bob))
    assert len(alice.get(f'/interest/{kind}').json) == 1
    assert outsider.get(f'/interest/{kind}?user_id={aid}').json == []
    assert FlaskClient(app, app.response_class).get(f'/interest/{kind}?user_id={aid}').status_code == 401
    record = alice.get(f'/interest/{kind}').json[0]
    assert set(record) == {'user_id', 'username', 'name', 'profile_id', 'since'}
    assert alice.post('/auth/logout', json={}, headers=csrf(alice)).status_code == 200
    assert alice.get(f'/interest/{kind}').status_code == 401
    assert len(bob.get(f'/interest/{kind}').json) == 1
