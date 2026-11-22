"""Browser contract and adversarial requests with CSRF fully enabled."""
import re
from html.parser import HTMLParser

import pytest
from flask.testing import FlaskClient
from werkzeug.security import check_password_hash

from app.auth import MIN_PASSWORD_LENGTH


@pytest.fixture
def raw_client(app):
    # Unlike the ordinary API fixture, never insert a CSRF header automatically.
    return FlaskClient(app, app.response_class)


def token(client):
    response = client.get('/auth/csrf')
    assert response.headers['Cache-Control'] == 'no-store'
    return response.json['csrf_token']


def post(client, path, payload):
    return client.post(path, json=payload, headers={'X-CSRF-Token': token(client)})


def account(**overrides):
    return {'username': 'roomie_user', 'email': 'roomie@washburn.edu',
            'password': 'password123', 'confirm_password': 'password123', **overrides}


def nav(client):
    return client.get('/').text.split('<nav', 1)[1].split('</nav>', 1)[0]


def test_real_registration_login_logout_navigation(raw_client, db):
    client = raw_client
    assert 'Get started' in nav(client)
    assert 'account-dropdown' not in nav(client)
    old_token = token(client)
    response = post(client, '/auth/register', account(next='/preferences'))
    assert response.status_code == 201
    assert response.json['redirect'] == '/profile/setup'
    assert isinstance(response.json['user']['id'], int)
    assert 'password_hash' not in response.json['user']
    row = db.execute('SELECT * FROM users').fetchone()
    assert check_password_hash(row['password_hash'], 'password123')
    assert row['password_hash'] != 'password123'
    assert token(client) != old_token
    page = client.get('/')
    assert 'Account created. You are now signed in.' in page.text
    navigation = nav(client)
    for text in ('roomie_user', 'My profile', 'Preferences', 'Log out', '/auth/logout'):
        assert text in navigation
    for text in ('>Log in<', 'Get started'):
        assert text not in navigation
    assert client.get('/auth/me').json['user']['username'] == 'roomie_user'
    for path in ('/profile/setup', '/preferences'):
        response = client.get(path)
        assert response.status_code == 200
        assert ('data-profile-form' if path == '/profile/setup' else 'data-preferences-overview') in response.text
    # Invalid/missing tokens must never log out the authenticated user.
    assert client.post('/auth/logout', json={}).status_code == 403
    assert client.get('/auth/me').status_code == 200
    assert post(client, '/auth/logout', {}).status_code == 200
    assert client.get('/auth/me').status_code == 401
    assert 'Get started' in nav(client)
    with client.session_transaction() as session:
        assert 'user_id' not in session
    response = post(client, '/auth/login', {'email': 'ROOMIE@washburn.edu',
                                          'password': 'password123', 'next': '/profile'})
    assert response.status_code == 200
    assert response.json['redirect'] == '/profile/setup'
    page = client.get('/')
    assert 'roomie_user' in page.text
    assert 'You are now signed in.' in page.text


@pytest.mark.parametrize('path', ['/profile', '/preferences'])
def test_private_pages_require_real_session(raw_client, path):
    response = raw_client.get(path + '?logged_in=true&user_id=1')
    assert response.status_code == 302
    assert response.location == '/login?next=' + path
    with raw_client.session_transaction() as session:
        session['user_id'] = 999999
    assert raw_client.get(path).status_code == 302


@pytest.mark.parametrize('path', ['/auth/register', '/auth/login', '/auth/logout'])
def test_csrf_missing_wrong_and_cross_session(app, raw_client, path):
    token(raw_client)
    for headers in ({}, {'X-CSRF-Token': 'wrong'}, {'X-CSRF-Token': 'é'}):
        response = raw_client.post(path, json=account(), headers=headers)
        assert response.status_code == 403
        assert 'security token' in response.json['error']
    other = FlaskClient(app, app.response_class)
    other_token = token(other)
    token(raw_client)
    assert raw_client.post(path, json=account(), headers={'X-CSRF-Token': other_token}).status_code == 403


def test_old_token_rejected_after_login_and_logout(raw_client):
    old = token(raw_client)
    assert post(raw_client, '/auth/register', account()).status_code == 201
    assert raw_client.post('/auth/logout', json={}, headers={'X-CSRF-Token': old}).status_code == 403
    logged_in_token = token(raw_client)
    assert post(raw_client, '/auth/logout', {}).status_code == 200
    assert raw_client.post('/auth/login', json=account(), headers={'X-CSRF-Token': logged_in_token}).status_code == 403


@pytest.mark.parametrize('path', ['/auth/register', '/auth/login', '/auth/logout'])
@pytest.mark.parametrize('body', ['null', '[]', 'true', '42', '"text"', '{broken', ''])
def test_malformed_json_is_400(raw_client, path, body):
    response = raw_client.post(path, data=body, content_type='application/json',
                               headers={'X-CSRF-Token': token(raw_client)})
    assert response.status_code == 400
    assert response.is_json


@pytest.mark.parametrize('path', ['/auth/register', '/auth/login', '/auth/logout'])
def test_non_json_is_415(raw_client, path):
    response = raw_client.post(path, data={'email': 'roomie@washburn.edu'},
                               headers={'X-CSRF-Token': token(raw_client)})
    assert response.status_code == 415
    assert response.is_json


@pytest.mark.parametrize('field', ['username', 'email', 'password', 'confirm_password'])
@pytest.mark.parametrize('value', [None, 5, [], {}])
def test_wrong_registration_field_types(raw_client, field, value):
    assert post(raw_client, '/auth/register', account(**{field: value})).status_code == 400


@pytest.mark.parametrize('field', ['email', 'password'])
@pytest.mark.parametrize('value', [None, 5, [], {}])
def test_wrong_login_field_types(raw_client, field, value):
    assert post(raw_client, '/auth/login', {field: value}).status_code == 400


def test_password_policy_and_confirmation(raw_client):
    html = raw_client.get('/register').text
    assert f'minlength="{MIN_PASSWORD_LENGTH}"' in html
    assert 'name="password"' in html and 'name="confirm_password"' in html
    assert 'action="/auth/register"' in html and 'data-auth-form' in html
    assert post(raw_client, '/auth/register', account(confirm_password='different')).status_code == 400
    assert post(raw_client, '/auth/register', account(password='a' * 7, confirm_password='a' * 7)).status_code == 400
    assert post(raw_client, '/auth/register', account(password='a' * 8, confirm_password='a' * 8)).status_code == 201


def test_real_registration_form_contract(raw_client):
    class Forms(HTMLParser):
        def __init__(self):
            super().__init__()
            self.forms = []
            self.current = None

        def handle_starttag(self, tag, attrs):
            if tag == 'form':
                self.current = {'attrs': dict(attrs), 'inputs': {}}
                self.forms.append(self.current)
            elif tag == 'input' and self.current is not None:
                attrs = dict(attrs)
                self.current['inputs'][attrs.get('name')] = attrs

        def handle_endtag(self, tag):
            if tag == 'form':
                self.current = None

    html = raw_client.get('/register').text
    parser = Forms()
    parser.feed(html)
    actual = [form for form in parser.forms if form['attrs'].get('action') == '/auth/register']
    assert len(actual) == 1
    form = actual[0]
    assert form['attrs']['method'].lower() == 'post'
    assert 'data-auth-form' in form['attrs']
    assert 'data-preview-form' not in html
    assert 'Account creation will be connected to the backend later.' not in html
    for name in ('password', 'confirm_password'):
        field = form['inputs'][name]
        assert field['type'] == 'password'
        assert field['autocomplete'] == 'new-password'
        assert field['minlength'] == str(MIN_PASSWORD_LENGTH)
        assert 'required' in field
        assert field['aria-describedby'] == 'registration-password-help'
    assert f'Use at least {MIN_PASSWORD_LENGTH} characters.' in html


@pytest.mark.parametrize('next_url', ['https://evil.example', '//evil.example', '/\\evil.example', '/auth/logout', '/profile?next=//evil.example', ['bad']])
def test_redirects_are_allowlisted(raw_client, next_url):
    response = post(raw_client, '/auth/register', account(next=next_url))
    assert response.status_code == 201
    assert response.json['redirect'] == '/profile/setup'


def test_cookie_flags_and_no_cache(raw_client):
    response = raw_client.get('/login')
    cookie = response.headers['Set-Cookie']
    for flag in ('Secure', 'HttpOnly', 'SameSite=Lax'):
        assert flag in cookie
    assert response.headers['Cache-Control'] == 'no-store'
    assert re.search(r'<meta name="csrf-token" content="[^"]+">', response.text)
    assert 'action="/auth/login"' in response.text
    assert raw_client.get('/auth/logout').status_code == 405


def test_csrf_also_protects_other_state_changing_apis(raw_client):
    for method, path in [('post', '/profiles'), ('put', '/profiles/me'),
                         ('post', '/interest/1'), ('delete', '/interest/1')]:
        assert getattr(raw_client, method)(path, json={}).status_code == 403
