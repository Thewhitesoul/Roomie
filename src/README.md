# Source Code

Roomie application code will be stored in this directory.

The planned implementation will separate:

- Flask application setup
- Routes and request handling
- User authentication
- Profile and preference logic
- Matching and filtering logic
- Database models and queries
- HTML templates and static files

The exact structure will be refined during the architecture milestone.

## Frontend preview

From the repository root, use the project environment (rather than Anaconda):

```bash
./.venv/bin/python -m flask --app src.preview run --debug --port 5002
```

Open http://127.0.0.1:5002/. Port 5001 also works when it is available.
The preview needs Flask from the root `requirements.txt`; there is no frontend build step.

The seven route definitions in `preview.py` serve the home, login, registration,
profile, preferences, matches, and individual profile pages. The three sample
profiles are fictional. Authentication, persistence, filtering, and interest
operations are not implemented. Form feedback intentionally makes no network
request and writes no browser storage. Submit controls remain disabled without
JavaScript; navigation remains available. Password inputs deliberately have no
submission names in this preview, as in the original templates.

### Frontend structure

- `templates/base.html` supplies shared navigation, an active-page indicator,
  stylesheet/script references, and the footer through Jinja inheritance.
- `url_for()` builds links from the existing route names. No logout or interest
  endpoints exist yet; connect these only when the backend provides them, along
  with authenticated POST handling and CSRF protection.
- `static/style.css` defines the shared palette with CSS custom properties,
  responsive grid layouts, solid form surfaces, and a solid navigation fallback
  enhanced with backdrop blur when supported. Initial artwork uses CSS only.
- `static/app.js` adds the mobile menu, Escape-key dismissal, password confirmation
  validation, and explicit preview feedback. Reduced-motion styling removes
  transitions when requested by the user's operating system.

### Authentication integration

The preview defaults to logged out. `/profile` and `/preferences` now redirect
anonymous requests to `/login?next=...`; public sample profiles and matches remain
available. No login, session, logout, or CSRF implementation exists in this branch.

The backend must load a verified user from its authenticated session on every
request into `g.current_user`, with `is_authenticated`, `display_name` (optional),
and `username`. Both navigation and private route guards use this same user.
Never populate it from request parameters or browser flags. If adopting
Flask-Login, adapt `authenticated_user()` to its verified `current_user` instead.

Before enabling authenticated requests, the backend must also provide:

- Real credential verification and session creation in login, replacing the
  preview form behavior. Validate any `next` destination as local before redirecting.
- A `logout` endpoint accepting POST only and the CSRF provider's `csrf_token()`
  template helper. The prepared logout form submits `csrf_token` to this endpoint.
  Enable server-side CSRF validation; reject invalid tokens before changing state.
- Logout that clears the authenticated session (and remember-me authentication,
  if used) and redirects home. Use the chosen authentication library's logout
  mechanism; do not merely change the displayed navigation.

Without these connections, successful login/logout cannot be demonstrated. No
fake login or unprotected logout endpoint has been introduced. The authenticated
layout deliberately requires the backend logout endpoint and CSRF helper.

### Verification

Run the executable server/template checks with:

```bash
./.venv/bin/python -m unittest discover -s tests -v
node --check src/static/app.js
```

Four tests cover public/logged-out navigation, registration links, private route
redirects, rejection of an unverified user, and the authenticated template contract
using explicit test-only user/URL/token fixtures. These fixtures do not implement
or verify a real login, logout, or CSRF validator. Private view access is checked
with rendering mocked because the backend logout and CSRF facilities are absent.

The dropdown supports native Enter/Space activation, Tab navigation, ArrowDown/Up
to open and focus its first/last control, Escape with focus restoration, outside
click dismissal, and closing when focus leaves. Without JavaScript its links and
POST form remain expanded and usable. At mobile widths the dropdown is in normal
flow with full-width controls. Browser interaction and mobile rendering have not
been verified; manually exercise these at 360px, 768px, and desktop widths before
merging. Real successful login, profile/preferences use, and logout must be tested
end to end after backend integration.
