# Roomie

Roomie is a CM333 Software Engineering group project that helps college students find compatible roommates. Users create profiles, enter lifestyle information and roommate preferences, view possible matches, and show interest in connecting.

## Problem

Finding a roommate is difficult when people do not have an organized way to compare habits, interests, housing needs, and preferences. Roomie is intended to make that process clearer while reminding users that they remain responsible for their own housing and safety decisions.

## Full System Vision

A fully developed version of Roomie could support:

- Account registration and login
- Roommate profiles and lifestyle preferences
- Potential roommate matching and filtering
- Room listings with price, location, and availability
- Saved profiles and listings
- Communication between interested users
- Notifications, reporting, and basic verification features

## Semester MVP

The semester MVP focuses on the shortest complete roommate-finding process:

1. Register and log in.
2. Create a roommate profile.
3. Enter interests, lifestyle information, and roommate preferences.
4. Find or filter possible roommate matches.
5. View another user's profile.
6. Show interest in connecting.

Detailed housing searches, real-time messaging, payments, background checks, advanced compatibility scoring, and lease management are outside the MVP.

## Implemented MVP

The local integration includes real registration/login/logout, profile onboarding
and editing, roommate discovery and filters, interest/withdrawal, mutual matches,
My Matches, incoming-interest notifications, and saved lifestyle preferences.
Other signed-in users can read the six shareable lifestyle settings on roommate
profiles. All application data persists in SQLite.

Discovery ranks by shared **profile interests** and filters profile budget,
location, and interests. Lifestyle preferences are displayed but do not currently
affect compatibility scoring. Profile and preference budgets remain separate.

See [the integration audit and merge checklist](docs/code-and-tests.md) and
[the frontend/backend guide](src/README.md).

## Technology

- Front end: HTML, CSS, and JavaScript
- Back end: Python and Flask
- Database: SQLite and SQL
- Testing: pytest and manual browser testing
- Project tools: GitHub, Trello, GroupMe, and Google Drive

## Repository Structure

```text
Roomie/
├── docs/
│   ├── database-design.md
│   ├── requirements.md
│   └── code-and-tests.md
├── src/
│   ├── roomie/app/       # Flask factory, APIs, SQLite schema/migrations
│   ├── roomie/tests/     # Backend and integration tests
│   ├── templates/       # Shared Jinja templates
│   ├── static/          # CSS and browser controllers
│   └── README.md
├── tests/
│   ├── browser/         # Chrome/CDP scenarios against temporary SQLite
│   └── README.md
├── .gitignore
├── README.md
├── pytest.ini
└── requirements.txt
```

Use `src/roomie/app:create_app` for the functional application. `src/preview.py`
is a legacy, unauthenticated visual preview used by separate smoke tests; it
does not save data and is not the MVP server.

## Getting Started

Use Python 3.11+ with SQLite and `hashlib.scrypt` support (audited on Python
3.13.3). Install from the reviewed integration checkout; the current local
uncommitted/untracked integration must be included before a fresh clone can
reproduce it. Direct Python dependencies are pinned to the tested versions.

```bash
git clone https://github.com/Thewhitesoul/Roomie.git
cd Roomie
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cd src/roomie
python -m flask --app app init-db
# Local HTTP only:
ROOMIE_COOKIE_SECURE=0 python -m flask --app app run --port 5002
```

Windows users can activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
# After installation and init-db, replace the Unix launch line with:
$env:ROOMIE_COOKIE_SECURE = "0"
python -m flask --app app run --port 5002
```

Open `http://127.0.0.1:5002/`; `/health` should return `{"status":"ok"}`.
Run `init-db` for a new database. It creates missing tables without deleting
existing records. For an existing database, use `flask --app app migrate-db` to
add missing onboarding columns; run `init-db` as well if tables are missing.
Keep the same SQLite file. Back it up before team upgrades and never replace it
with a test database.

`SECRET_KEY` comes from the environment or ignored
`src/roomie/instance/config.py`. A random development key is generated when it
is absent, so development restarts invalidate sessions but preserve account
data. Configure one stable random key for shared deployments. Secure cookies
default on; production needs HTTPS, debug off, and a production WSGI server.
Do not use the local HTTP cookie override in production. `.env` is ignored;
automatic dotenv loading is not a required dependency—set environment variables
explicitly or use the instance config file.

## Verification

From the repository root, with the environment activated:

```bash
python -m pytest -q
python tests/browser/run_profile.py
```

The Chrome runner requires Node 24 and Chrome. Set `ROOMIE_CHROME_EXECUTABLE` if
Chrome is not at its default macOS path. It uses separate browser cookie jars
and a temporary SQLite database, including a real one-minute polling check.
It never tests against the development database. See the audit for exact counts
and manual two-user steps. Windows browser execution and Firefox/Safari/Edge
have not been verified by this audit.

## Team Workflow

- Keep `main` in a usable state.
- Create a separate branch for each feature or major task.
- Use descriptive commit messages.
- Review changes before merging them into `main`.
- Do not commit passwords, secret keys, virtual environments, or local database files.

## Team

- Stuti — Project Manager, Documentation, and Database
- Swikar — UI/UX and Frontend
- Arpan — Backend
- Rajju — Testing/QA and Integration
