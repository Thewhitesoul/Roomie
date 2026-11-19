# Source Code

Roomie is a single Flask app in `src/roomie/app/`. It serves both the HTML pages
and the JSON API.

```
src/roomie/
  app/
    __init__.py     create_app(): config, database, blueprints
    auth.py         /api/auth      register, login, logout, me
    profile.py      /api/profiles  create, view, update profiles
    matches.py      /api/matches   ranked matches with filters
    interests.py    /api/interest  show/withdraw interest, sent/received/mutual
    pages.py        /              HTML pages
    db.py           SQLite connection and the init-db command
    schema.sql      database tables
    templates/      Jinja templates (base.html plus one per page)
    static/         style.css and app.js
  instance/         roomie.sqlite (created locally, not committed)
  tests/            pytest suite
```

## Running the app

From `src/roomie`:

```powershell
flask --app app init-db      # first time only: creates instance/roomie.sqlite
flask --app app run --debug
```

Open http://127.0.0.1:5000/. If `flask` is not on your PATH, use
`python -m flask` instead. `init-db` wipes the database, so run it again only
when you want a fresh start.

## Pages and API

| Pages (HTML) | API (JSON) |
|---|---|
| `/` home | `/api/auth/register`, `/api/auth/login`, `/api/auth/logout`, `/api/auth/me` |
| `/login`, `/register` | `/api/profiles`, `/api/profiles/me`, `/api/profiles/<id>` |
| `/matches`, `/profiles/<id>` | `/api/matches` |
| `/profile`, `/preferences` (login required) | `/api/interest/<id>`, `/api/interest/sent`, `/received`, `/mutual` |
| `/logout` (POST) | `/health` |

Pages and the API share one session, so logging in through the API also logs
you in on the pages. Logged-out users who open `/profile` or `/preferences` are
redirected to `/login?next=...`.

### Current limitations

- The login, register, profile and preferences forms are still preview-only:
  `static/app.js` intercepts any form marked `data-preview-form` and shows a
  "Preview only" message instead of submitting. The "show interest" button works
  the same way.
- The home, matches and profile pages show three fictional sample profiles
  (`SAMPLE_PROFILES` in `pages.py`), not data from the database.
- The profile and preferences forms contain fields the database does not store
  yet (for example `age`, `housing_status`, `cleanliness`).

## Running the tests

From `src/roomie`:

```powershell
python -m pytest tests -v
```

pytest must be run from `src/roomie`; from the repo root the tests cannot import
`app`. See `tests/README.md` at the repo root for the test plan and results.
