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

### Verification

Flask test-client checks passed for all nine page URLs (including three individual
profiles), all linked pages and static assets, an empty matches list, and a 404
for an unknown profile. Preview form endpoints reject POST requests. JavaScript
syntax passed `node --check src/static/app.js`, and the running homepage returned
HTTP 200 on port 5002. There are no executable tests in `tests/` yet.

Browser rendering and interaction checks have not been performed. Before merging,
check 360px, 768px, and desktop widths for overflow; exercise the mobile menu,
keyboard focus, form validation, profile links, and preview interest feedback.
