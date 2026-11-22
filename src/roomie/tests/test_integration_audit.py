"""Regression checks for defects found during the local MVP integration audit."""
from html.parser import HTMLParser

import pytest

from app.db import SQLITE_MAX_INTEGER


@pytest.fixture
def audit_client(client):
    assert client.post('/auth/register', json={
        'username': 'audit_user', 'email': 'audit@washburn.edu', 'password': 'password123',
    }).status_code == 201
    assert client.post('/profiles', json={
        'name': 'Audit User', 'age': 24, 'housing_status': 'needs_housing',
        'preferred_location': 'Topeka', 'budget': 700,
    }).status_code == 201
    return client


@pytest.mark.parametrize('field,value', [
    ('min_budget', '²'), ('max_budget', '²'), ('limit', '²'),
    ('min_budget', str(SQLITE_MAX_INTEGER + 1)),
    ('max_budget', str(SQLITE_MAX_INTEGER + 1)),
    ('min_budget', '9' * 4400), ('max_budget', '9' * 4400), ('limit', '9' * 4400),
])
def test_invalid_numeric_filters_are_400_in_api_and_html(audit_client, field, value):
    for path in ('/matches', '/find-roommates'):
        response = audit_client.get(path, query_string={field: value})
        assert response.status_code == 400
        if path == '/matches':
            assert response.json['error']
        else:
            assert 'role="alert"' in response.text


@pytest.mark.parametrize('method', ['POST', 'PUT'])
@pytest.mark.parametrize('value', [SQLITE_MAX_INTEGER + 1, 2 ** 100])
def test_budget_overflow_is_rejected_before_sqlite_and_preserves_profile(client, method, value):
    assert client.post('/auth/register', json={
        'username': 'overflow_user', 'email': 'overflow@washburn.edu', 'password': 'password123',
    }).status_code == 201
    data = {'name': 'Original', 'age': 21, 'housing_status': 'has_housing',
            'preferred_location': 'Topeka', 'budget': 700}
    if method == 'PUT':
        assert client.post('/profiles', json=data).status_code == 201
    before = client.get('/profiles/me')
    response = client.open('/profiles' if method == 'POST' else '/profiles/me',
                           method=method, json={**data, 'name': 'Must not save', 'budget': value})
    assert response.status_code == 400
    assert 'Budget' in response.json['error']
    after = client.get('/profiles/me')
    assert after.status_code == before.status_code
    assert after.json == before.json


@pytest.mark.parametrize('method,prefix', [
    ('GET', '/profiles/'), ('GET', '/roommate/'), ('GET', '/preferences/profile/'),
    ('POST', '/interest/'), ('DELETE', '/interest/'),
])
@pytest.mark.parametrize('identifier', [str(SQLITE_MAX_INTEGER + 1), '9' * 4400])
def test_out_of_range_and_overlong_ids_are_404(audit_client, method, prefix, identifier):
    response = audit_client.open(prefix + identifier, method=method, json={} if method != 'GET' else None)
    assert response.status_code == 404
    assert audit_client.get('/interest/sent').json == []


def test_valid_sqlite_id_boundary_still_routes_and_is_not_found(audit_client):
    assert audit_client.get(f'/profiles/{SQLITE_MAX_INTEGER}').status_code == 404
    assert audit_client.get('/roommate/0').status_code == 404
    assert 'data-profile-url="/roommate/0"' in audit_client.get('/my-matches').text


@pytest.mark.parametrize('path', [
    '/auth/me', '/profiles', '/profiles/me', '/matches', '/preferences/me',
    '/preferences/profile/1', '/interest/sent', '/interest/received', '/interest/mutual',
])
def test_authenticated_api_data_is_not_cacheable(audit_client, path):
    response = audit_client.get(path)
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'no-store'


def test_registered_routes_have_no_method_collisions(app):
    seen = set()
    for rule in app.url_map.iter_rules():
        for method in rule.methods - {'HEAD', 'OPTIONS'}:
            key = method, rule.rule
            assert key not in seen, key
            seen.add(key)


class Links(HTMLParser):
    def __init__(self, source):
        super().__init__()
        self.urls = set()
        self.feed(source)

    def handle_starttag(self, tag, pairs):
        attrs = dict(pairs)
        key = 'src' if tag == 'script' else 'href' if tag in {'a', 'link'} else None
        value = attrs.get(key, '')
        if value.startswith('/') and not value.startswith('//'):
            self.urls.add(value)


def test_all_shared_page_links_and_assets_resolve(audit_client):
    urls = set()
    for path in ('/', '/login', '/register', '/profile', '/profile/setup', '/profile/edit',
                 '/preferences', '/preferences/edit', '/find-roommates', '/roommate/1', '/my-matches'):
        response = audit_client.get(path, follow_redirects=True)
        assert response.status_code == 200
        urls.update(Links(response.text).urls)
    for url in urls:
        assert audit_client.get(url, follow_redirects=True).status_code == 200, url
