"""Preview checks; injected users are template fixtures, not a login flow."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from flask import g, render_template

from src.preview import app


class NavigationTests(unittest.TestCase):
    def test_public_navigation_and_registration(self):
        client = app.test_client()
        for path in ('/', '/matches', '/login', '/register'):
            response = client.get(path)
            self.assertEqual(response.status_code, 200)
            nav = response.text.split('<nav', 1)[1].split('</nav>', 1)[0]
            for label in ('Home', 'Find roommates', 'Log in', 'Get started'):
                self.assertIn(label, nav)
            for label in ('My profile', 'Preferences', 'account-dropdown'):
                self.assertNotIn(label, nav)
            self.assertIn('href="/register"', nav)
        self.assertIn('Create your account', client.get('/register').text)

    def test_private_routes_redirect(self):
        for path in ('/profile', '/preferences'):
            response = app.test_client().get(path)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.location, '/login?next=' + path)

    def test_unverified_user_is_rejected(self):
        with app.test_request_context('/profile'):
            g.current_user = SimpleNamespace(is_authenticated=False)
            self.assertEqual(app.full_dispatch_request().status_code, 302)

    def test_backend_user_contract_and_private_pages(self):
        # Supply only URL building and token rendering for the future backend.
        # This does not register a functional logout or authenticate a client.
        for name in ('Sam', ''):
            with app.test_request_context('/'):
                g.current_user = SimpleNamespace(
                    is_authenticated=True, display_name=name, username='sam_user'
                )
                original_url_for = app.url_for
                def backend_url(endpoint, **values):
                    return '/logout' if endpoint == 'logout' else original_url_for(endpoint, **values)
                with patch.object(app, 'url_for', side_effect=backend_url):
                    html = render_template('base.html', csrf_token=lambda: 'test-token')
                self.assertIn('sam_user', html)
                self.assertIn('action="/logout"', html)
                self.assertIn('method="post"', html)
                self.assertIn('value="test-token"', html)
                self.assertIn('href="/profile"', html)
                self.assertIn('href="/preferences"', html)
                self.assertNotIn('Get started', html)
                self.assertNotIn('>Log in<', html)
        # Render the actual protected views with a verified backend user fixture.
        for path in ('/profile', '/preferences'):
            with app.test_request_context(path):
                g.current_user = SimpleNamespace(is_authenticated=True)
                with patch('src.preview.render_template', return_value='private page'):
                    self.assertEqual(app.full_dispatch_request().status_code, 200)



if __name__ == '__main__':
    unittest.main()
