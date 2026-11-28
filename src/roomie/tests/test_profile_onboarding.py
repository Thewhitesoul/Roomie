"""Real onboarding, additive migrations, saved overview, isolation, and CSRF."""
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.db import get_db, init_db, migrate_profiles
from app.profile_state import is_complete


def token(client):
    return {'X-CSRF-Token': client.get('/auth/csrf').json['csrf_token']}


def post(client, path, data):
    return client.post(path, json=data, headers=token(client))


def signup(client, username='onboarding', **extra):
    response = post(client, '/auth/register', {
        'username': username, 'email': f'{username}@washburn.edu', 'password': 'password123', **extra,
    })
    assert response.status_code == 201
    return response


def complete(**extra):
    return {'name': 'Chosen Name', 'age': 24, 'preferred_location': 'Topeka',
            'housing_status': 'needs_housing', 'bio': 'Hello future roommates.',
            'budget': 700, 'interests': ['cooking', 'hiking'], **extra}


def login(client, **extra):
    return post(client, '/auth/login', {'email': 'onboarding@washburn.edu', 'password': 'password123', **extra})


def test_registration_authenticates_and_requires_setup(client):
    response = signup(client, next='/preferences')
    assert response.json['redirect'] == '/profile/setup'
    assert client.get('/auth/me').status_code == 200
    assert client.get('/profiles/me').status_code == 404
    assert client.get('/profile').location == '/profile/setup'
    setup = client.get('/profile/setup')
    assert setup.status_code == 200
    assert 'Save and continue' in setup.text
    assert 'onboarding' in setup.text  # Username fallback in the account button.
    assert post(client, '/profiles', complete()).status_code == 201
    # Original intended destination survives setup exactly once, without a loop.
    assert client.get('/profile').location == '/preferences'
    assert client.get('/profile').status_code == 200
    assert client.get('/profile/setup').location == '/profile'


def test_completed_login_default_and_intended_destination(client):
    signup(client)
    assert post(client, '/profiles', complete()).status_code == 201
    for intended, expected in [(None, '/profile'), ('/find-roommates?interest=cooking', '/find-roommates?interest=cooking'),
                               ('/roommate/1', '/roommate/1'), ('/profile/edit', '/profile/edit')]:
        post(client, '/auth/logout', {})
        response = login(client, next=intended)
        assert response.status_code == 200
        assert response.json['redirect'] == expected
    assert client.get('/profile').status_code == 200
    assert client.get('/profile/setup', follow_redirects=True).request.path == '/profile'


@pytest.mark.parametrize('destination', ['https://evil.example', '//evil.example', '/\\evil.example',
    '/auth/logout', '/login', '/register', '/profile/setup', '/profile?next=//evil.example', '/%2f%2fevil.example', '/profile\r\nX:bad', [], 5])
def test_completed_login_rejects_unsafe_and_looping_next(client, destination):
    signup(client)
    post(client, '/profiles', complete())
    post(client, '/auth/logout', {})
    assert login(client, next=destination).json['redirect'] == '/profile'


def test_existing_incomplete_login_prefills_all_fields(client, app):
    signup(client)
    with app.app_context():
        connection = get_db()
        connection.execute('''INSERT INTO profiles
            (user_id, name, age, preferred_location, budget, bio, housing_status)
            VALUES (1, 'Legacy name', 29, 'Lawrence', 0, 'Saved bio', NULL)''')
        pid = connection.execute('SELECT id FROM profiles').fetchone()['id']
        connection.execute('INSERT INTO profile_interests VALUES (?, ?)', (pid, 'music'))
        connection.commit()
    post(client, '/auth/logout', {})
    assert login(client).json['redirect'] == '/profile/setup'
    page = client.get('/profile/setup')
    for text in ('value="Legacy name"', 'value="29"', 'value="Lawrence"', 'value="0"', 'Saved bio', 'music'):
        assert text in page.text
    assert 'Legacy name' in page.text.split('account-toggle', 1)[1].split('</button>', 1)[0]
    response = client.put('/profiles/me', json=complete(name='Legacy name', age=29, budget=0,
        preferred_location='Lawrence', bio='Saved bio', interests=['music']), headers=token(client))
    assert response.status_code == 200
    assert response.json['id'] == pid
    assert client.get('/profile').status_code == 200
    post(client, '/auth/logout', {})
    assert login(client).json['redirect'] == '/profile'


def test_saved_overview_edit_and_cancel(client):
    signup(client)
    post(client, '/profiles', complete())
    saved = client.get('/profiles/me').json
    page = client.get('/profile')
    assert page.status_code == 200
    for value in ('Chosen Name', '24', 'Topeka', 'I need housing', '$700/month', 'cooking', 'Hello future roommates.', 'profile-avatar'):
        assert value in page.text
    assert 'data-profile-form' not in page.text
    assert 'href="/profile/edit"' in page.text
    edit = client.get('/profile/edit?user_id=999')
    assert edit.status_code == 200
    for value in ('value="Chosen Name"', 'value="24"', 'value="700"', 'value="needs_housing" selected', '>Cancel</a>'):
        assert value in edit.text
    # Cancel is a GET link, with no writes, flashes of fake success, or ID changes.
    assert client.get('/profile').status_code == 200
    assert client.get('/profiles/me').json == saved
    updated = client.put('/profiles/me', json=complete(name='Updated', age=30, housing_status='has_housing'), headers=token(client))
    assert updated.status_code == 200
    assert updated.json['id'] == saved['id']
    page = client.get('/profile')
    assert 'Profile saved.' in page.text
    assert 'Updated' in page.text and 'I already have housing' in page.text


@pytest.mark.parametrize('fields', [
    {'age': None}, {'age': True}, {'age': 17}, {'age': 121}, {'age': 21.5}, {'age': '21'},
    {'housing_status': None}, {'housing_status': ''}, {'housing_status': 'other'}, {'housing_status': []},
    {'preferred_location': ''}, {'preferred_location': '  '}, {'name': '  '},
    {'budget': -1}, {'budget': True}, {'budget': 5.5}, {'bio': 'b' * 501},
    {'interests': ['x'] * 11}, {'interests': ['x' * 31]},
])
def test_required_values_and_constraints(client, fields):
    signup(client)
    response = post(client, '/profiles', complete(**fields))
    assert response.status_code == 400
    assert response.json['error']
    assert client.get('/profiles/me').status_code == 404
    assert post(client, '/profiles', complete()).status_code == 201
    assert client.put('/profiles/me', json=fields, headers=token(client)).status_code == 400
    assert client.get('/profiles/me').json['age'] == 24


@pytest.mark.parametrize('missing', ['name', 'age', 'preferred_location', 'housing_status'])
def test_create_requires_all_onboarding_fields(client, missing):
    signup(client)
    values = complete()
    values.pop(missing)
    assert post(client, '/profiles', values).status_code == 400


@pytest.mark.parametrize('age', [18, 120])
def test_age_boundaries_and_zero_budget(client, age):
    signup(client)
    response = post(client, '/profiles', complete(age=age, budget=0))
    assert response.status_code == 201
    assert is_complete(response.json)
    assert '$0/month' in client.get('/profile').text


@pytest.mark.parametrize('path', ['/profile', '/profile/setup', '/profile/edit'])
def test_profile_pages_require_session(client, path):
    assert client.get(path).location == '/login?next=' + path
    assert client.get(path + '?logged_in=true&user_id=1').status_code == 302


def test_csrf_and_account_isolation(app):
    alice, bob = (FlaskClient(app, app.response_class) for _ in range(2))
    signup(alice, username='alice')
    assert alice.post('/profiles', json=complete()).status_code == 403
    saved = post(alice, '/profiles', complete()).json
    signup(bob, username='bob')
    assert bob.get('/profiles/me').status_code == 404
    assert bob.get('/profile/edit?user_id=1').location == '/profile/setup'
    assert bob.put('/profiles/me', json=complete(), headers=token(bob)).status_code == 404
    assert alice.put('/profiles/me', json={'age': 30}, headers={'X-CSRF-Token': 'wrong'}).status_code == 403
    assert alice.get('/profiles/me').json == saved
    assert post(bob, '/profiles', complete(name='Bob', user_id=1)).json['user_id'] != saved['user_id']
    assert alice.get('/profiles/me').json['name'] == 'Chosen Name'


def test_public_profile_does_not_expose_credentials(client):
    signup(client)
    post(client, '/profiles', complete())
    response = client.get('/roommate/1')
    assert 'onboarding@washburn.edu' not in response.text
    assert 'password123' not in response.text and 'password_hash' not in response.text
    assert 'email' not in client.get('/profiles/1').json


def legacy_database(path):
    # Use the exact prior schema shape, with existing rows and relationships.
    schema = (Path(__file__).parents[1] / 'app/schema.sql').read_text()
    schema = '\n'.join(line for line in schema.splitlines() if not line.strip().startswith(('age INTEGER', 'housing_status TEXT')))
    connection = sqlite3.connect(path)
    connection.executescript(schema)
    connection.executescript('''
        INSERT INTO users(id, username, email, password_hash) VALUES(10, 'legacy', 'legacy@washburn.edu', 'hash');
        INSERT INTO users(id, username, email, password_hash) VALUES(11, 'peer', 'peer@washburn.edu', 'peer-hash');
        INSERT INTO profiles(id, user_id, name, bio, preferred_location, budget) VALUES(42, 10, 'Legacy', 'Bio', 'Topeka', 650);
        INSERT INTO profile_interests VALUES(42, 'music');
        INSERT INTO connection_requests(from_user_id,to_user_id) VALUES(10,11);
        INSERT INTO preferences(user_id,cleanliness) VALUES(10,'tidy');
    ''')
    connection.close()


def test_legacy_migration_preserves_all_data_and_is_idempotent(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    legacy_database(path)
    before = sqlite3.connect(path)
    snapshots = {}
    for table in ('users', 'profiles', 'profile_interests', 'connection_requests', 'preferences'):
        columns = [row[1] for row in before.execute(f'PRAGMA table_info({table})')]
        snapshots[table] = (columns, before.execute(f'SELECT * FROM {table} ORDER BY rowid').fetchall())
    before.close()
    app = create_app({'TESTING': True, 'DATABASE': str(path), 'SECRET_KEY': 'migration-test'})
    # The CLI and normal first DB use both apply the same non-destructive upgrade.
    result = app.test_cli_runner().invoke(args=['migrate-db'])
    assert result.exit_code == 0
    with app.app_context():
        for table, (columns, rows) in snapshots.items():
            query = f"SELECT {','.join(columns)} FROM {table} ORDER BY rowid"
            assert [tuple(row) for row in get_db().execute(query)] == rows
    for _ in range(2):
        with app.app_context():
            connection = get_db()
            row = connection.execute('SELECT * FROM profiles WHERE id=42').fetchone()
            assert dict(row) | {'age': None, 'housing_status': None} == dict(row)
            assert row['name'] == 'Legacy' and row['budget'] == 650 and row['user_id'] == 10
            assert connection.execute('SELECT interest FROM profile_interests WHERE profile_id=42').fetchone()[0] == 'music'
            assert connection.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 2
            assert connection.execute('SELECT COUNT(*) FROM connection_requests').fetchone()[0] == 1
            assert connection.execute('SELECT cleanliness FROM preferences').fetchone()[0] == 'tidy'
            assert not is_complete(row)
            init_db()  # Reinitialization also preserves existing rows.
            connection.execute("INSERT INTO profiles(user_id,name) VALUES(11,'Peer')") if _ == 0 else None
            connection.commit()
            assert connection.execute('SELECT id FROM profiles WHERE user_id=11').fetchone()[0] == 43
    assert app.test_cli_runner().invoke(args=['migrate-db']).exit_code == 0


def test_automatic_migration_and_transaction_rollback(tmp_path):
    path = tmp_path / 'legacy.sqlite'
    legacy_database(path)
    connection = sqlite3.connect(path)
    from app.db import PROFILE_ADDITIONS
    with patch.dict(PROFILE_ADDITIONS, {'housing_status': 'BROKEN CHECK ('}):
        with pytest.raises(sqlite3.OperationalError):
            migrate_profiles(connection)
    assert 'age' not in {row[1] for row in connection.execute('PRAGMA table_info(profiles)')}
    connection.close()
    restarted = create_app({'TESTING': True, 'DATABASE': str(path)})
    with restarted.app_context():
        assert get_db().execute('SELECT age, housing_status FROM profiles WHERE id=42').fetchone() is not None


@pytest.mark.parametrize('assignment', ["age=17", "age=121", "age=21.5", "age='abc'", "housing_status='other'"])
def test_database_constraints_after_migration(tmp_path, assignment):
    path = tmp_path / 'legacy.sqlite'
    legacy_database(path)
    app = create_app({'TESTING': True, 'DATABASE': str(path)})
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute('UPDATE profiles SET ' + assignment + ' WHERE id=42')


@pytest.mark.parametrize('assignment', ["age=17", "age=121", "age=21.5", "age='abc'", "housing_status='other'"])
def test_fresh_schema_has_same_constraints(client, app, assignment):
    signup(client)
    post(client, '/profiles', complete())
    with app.app_context():
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute('UPDATE profiles SET ' + assignment)


@pytest.mark.parametrize('payload', [[], None, True, 3])
def test_profile_rejects_non_object_json(client, payload):
    signup(client)
    for method, path in [(client.post, '/profiles'), (client.put, '/profiles/me')]:
        import json
        response = method(path, data=json.dumps(payload), content_type='application/json', headers=token(client))
        assert response.status_code == 400
        assert response.is_json


def test_duplicate_create_race_returns_conflict_without_another_profile(client, app):
    signup(client)
    saved = post(client, '/profiles', complete()).json
    with app.app_context():
        existing = dict(get_db().execute('SELECT * FROM profiles').fetchone())
    # Model another request creating the row after the first existence check.
    with patch('app.profile._my_profile', side_effect=[None, existing]):
        assert post(client, '/profiles', complete()).status_code == 409
    assert client.get('/profiles/me').json == saved
    assert len(client.get('/profiles').json) == 1


def test_account_name_fallback_and_optional_values(client, app):
    signup(client)
    with app.app_context():
        get_db().execute("INSERT INTO profiles(user_id,name) VALUES(1,' ')")
        get_db().commit()
    page = client.get('/profile/setup')
    assert 'onboarding' in page.text.split('account-toggle', 1)[1].split('</button>', 1)[0]
    response = client.put('/profiles/me', json=complete(budget=None, bio='', interests=[]), headers=token(client))
    assert response.status_code == 200
    page = client.get('/profile')
    assert page.status_code == 200
    assert 'Not added yet' in page.text and 'No biography added yet.' in page.text
    assert 'No interests added yet.' in page.text
