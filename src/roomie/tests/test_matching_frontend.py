"""HTML matching uses the existing API handlers and real SQLite profiles."""
from html.parser import HTMLParser
from urllib.parse import urlencode

import pytest


def signup(client, username):
    client.post('/auth/logout', json={})
    response = client.post('/auth/register', json={
        'username': username, 'email': f'{username}@washburn.edu', 'password': 'password123',
    })
    assert response.status_code == 201
    return response.json['user']['id']


def make_profile(client, **values):
    response = client.post('/profiles', json={'age': 21, 'housing_status': 'needs_housing', 'preferred_location': 'Topeka', **values})
    assert response.status_code == 201
    return response.json


@pytest.fixture
def neighborhood(client):
    signup(client, 'no_profile')  # Ensure profile IDs differ from user IDs.
    signup(client, 'dana')
    dana = make_profile(client, name='Dana', preferred_location='Topeka', bio='Quiet and tidy.',
                        budget=600, interests=['cooking', 'gaming'])
    signup(client, 'river')
    river = make_profile(client, name='River', preferred_location='Lawrence', bio='Music fan.',
                         budget=900, interests=['hiking'])
    signup(client, 'kai')
    kai = make_profile(client, name='Kai', preferred_location='Topeka', bio='', interests=['cooking'])
    signup(client, 'myself')
    me = make_profile(client, name='My own profile', preferred_location='Topeka',
                      budget=700, interests=['cooking', 'gaming'])
    return client, dana, river, kai, me


class Cards(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.ids = []
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'article' and 'data-profile-id' in attrs:
            self.ids.append(int(attrs['data-profile-id']))
        if tag == 'a' and attrs.get('href', '').startswith('/roommate/'):
            self.links.append(attrs['href'])


def test_real_results_preserve_ranking_and_profile_links(neighborhood):
    client, dana, river, kai, me = neighborhood
    api = client.get('/matches')
    page = client.get('/find-roommates')
    assert api.is_json and page.mimetype == 'text/html'
    assert page.status_code == 200
    cards = Cards(page.text)
    assert cards.ids == [p['id'] for p in api.json] == [dana['id'], kai['id'], river['id']]
    assert me['id'] not in cards.ids
    assert cards.links == [f'/roommate/{pid}' for pid in cards.ids]
    assert dana['id'] != dana['user_id']
    for text in ('Dana', 'Topeka', 'Quiet and tidy.', '$600/month', 'cooking', 'gaming'):
        assert text in page.text
    assert 'My own profile' not in page.text.split('<main', 1)[1]
    assert 'fictional' not in page.text.lower()


@pytest.mark.parametrize('query,expected', [
    ('max_budget=700', ['Dana']), ('min_budget=800', ['River']),
    ('min_budget=650&max_budget=950', ['River']), ('location=TOPE', ['Dana', 'Kai']),
    ('interest=hiking', ['River']), ('interest=cooking&interest=hiking', ['Dana', 'Kai', 'River']),
    ('location=topeka&max_budget=650&interest=gaming', ['Dana']), ('limit=1', ['Dana']),
])
def test_filters_use_existing_api(neighborhood, query, expected):
    client = neighborhood[0]
    api = client.get('/matches?' + query)
    response = client.get('/find-roommates?' + query)
    assert response.status_code == 200
    assert [p['name'] for p in api.json] == expected
    assert Cards(response.text).ids == [p['id'] for p in api.json]


def test_comma_separated_form_uses_repeated_api_parameters(neighborhood):
    client = neighborhood[0]
    response = client.get('/find-roommates?' + urlencode({
        'min_budget': '0', 'max_budget': '900', 'location': 'Topeka', 'interests': ' cooking, , gaming ',
    }), follow_redirects=True)
    assert response.status_code == 200
    assert response.request.args.getlist('interest') == ['cooking', 'gaming']
    assert Cards(response.text).ids == [neighborhood[1]['id']]
    assert 'value="cooking, gaming"' in response.text
    assert 'value="900"' in response.text


@pytest.mark.parametrize('query', ['min_budget=900&max_budget=500', 'max_budget=nope', 'min_budget=-1'])
def test_invalid_filters_show_api_error(neighborhood, query):
    client = neighborhood[0]
    response = client.get('/find-roommates?' + query)
    assert response.status_code == 400
    assert client.get('/matches?' + query).json['error'] in response.text
    assert Cards(response.text).ids == []
    assert 'role="alert"' in response.text
    assert 'No roommates match' not in response.text  # Errors aren't empty results.


def test_empty_results_and_missing_profile(client):
    signup(client, 'alone')
    make_profile(client, name='My own profile')
    response = client.get('/find-roommates')
    assert response.status_code == 200
    assert 'No roommates match' in response.text
    assert Cards(response.text).ids == []
    assert 'My own profile' not in response.text.split('<main', 1)[1]
    response = client.get('/roommate/99999')
    assert response.status_code == 404
    assert 'Profile unavailable' in response.text
    assert client.get('/profiles/99999').status_code == 404


def test_profile_detail_uses_profile_id_not_user_id(neighborhood):
    client, dana, river, *_ = neighborhood
    response = client.get(f'/roommate/{dana["id"]}')
    assert response.status_code == 200
    assert Cards(response.text).ids == [dana['id']]
    assert '<h1>Dana</h1>' in response.text
    assert '<h1>River</h1>' not in response.text
    assert '$600/month' in response.text
    assert 'Show Interest' in response.text
    assert f'data-action-url="/interest/{dana["user_id"]}"' in response.text
    assert 'data-interest-action="send" disabled' in response.text
    assert 'data-interest-panel' in response.text
    assert client.get(f'/profiles/{dana["id"]}').json['name'] == 'Dana'
    assert client.get('/interest/sent').json == []


def test_optional_fields_zero_budget_and_escaping(client):
    signup(client, 'untrusted')
    malicious = '<img src=x onerror=alert(1)>'
    saved = make_profile(client, name=malicious, bio='<script>alert(1)</script>',
                         preferred_location='<b>Town</b>', interests=['<svg/onload=alert(1)>'], budget=0)
    signup(client, 'reader')
    for path in ('/find-roommates', f'/roommate/{saved["id"]}', '/'):
        response = client.get(path)
        assert malicious not in response.text
        assert '<script>alert(1)</script>' not in response.text
        assert '&lt;img' in response.text
    response = client.get(f'/roommate/{saved["id"]}')
    assert '$0/month' in response.text
    assert '&lt;svg/onload=alert(1)&gt;' in response.text


@pytest.mark.parametrize('path', ['/find-roommates', '/roommate/1', '/roommate/999'])
def test_html_authentication(client, path):
    response = client.get(path + '?logged_in=true&user_id=1')
    assert response.status_code == 302
    assert response.location == '/login'
    assert client.get('/matches').status_code == 401
    assert client.get('/profiles/1').status_code == 401


def test_home_uses_real_profiles_and_never_own_profile(neighborhood):
    client, dana, *_ = neighborhood
    response = client.get('/')
    assert 'My own profile' not in response.text.split('<main', 1)[1]
    assert 'Dana' in response.text
    assert f'/roommate/{dana["id"]}' in response.text
    assert 'Preview profile' not in response.text
