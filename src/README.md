# Roomie frontend and backend

The existing backend factory in `src/roomie/app/__init__.py` serves the shared
`src/templates` and `src/static` directories. `GET /` renders the existing Roomie
homepage, real matching cards, and profile details; `/health` still returns `{"status":"ok"}`.

## Run locally

From the repository root:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cd src/roomie
# For a new database only:
python -m flask --app app init-db
# For an existing database (additive, preserves all records):
python -m flask --app app migrate-db
# HTTP development only; production must use Secure cookies over HTTPS.
ROOMIE_COOKIE_SECURE=0 python -m flask --app app run --debug --port 5002
```

Open `http://127.0.0.1:5002/`. Use the backend app, not `src.preview`, for real
accounts. SQLite is the only persistent application store. Profile onboarding
adds nullable age/housing columns through a transactional migration. Read the
[migration and profile guide](../docs/profile-integration.md) before upgrading.
`init-db` and `migrate-db` preserve existing records.

## Authentication contract

- `/register` and `/login` render the existing styled forms. JavaScript submits
  JSON to `/auth/register` and `/auth/login`, with same-origin credentials and an
  `X-CSRF-Token` header. Buttons are disabled without JavaScript, with a clear
  explanation. No passwords or auth tokens are written to browser storage.
- The existing backend policy is **8 characters minimum** (also documented in
  `docs/code-and-tests.md`). The previous preview required 12. Registration now
  renders the minimum from `auth.MIN_PASSWORD_LENGTH`; backend policy is unchanged.
  The browser requires matching confirmation, and the API validates
  `confirm_password` when supplied. It remains optional for existing API clients.
- Authentication APIs accept JSON objects only: unsupported content types return JSON 415;
  malformed JSON, arrays/scalars, and incorrectly typed credential fields return
  JSON 400. Validation and duplicate-account errors are displayed using text,
  never HTML. Unknown-email and wrong-password login errors remain identical.
- Registration/login preserve SQLite integer user IDs, Werkzeug password hashing,
  and the existing `session['user_id']` / `g.user` mechanism. The navigation reads
  `g.user` directly, shows the saved display name (falling back to username), and hides the registration CTA
  and Log in after authentication. No preview user can authenticate a request.
- Logout submits JSON to the existing POST `/auth/logout`, clears the session,
  and returns home. GET logout is not supported. Success messages appear after
  navigation using Flask flash messages. Registration and incomplete-profile login
  go to `/profile/setup`. Completed-profile login returns to a safe intended GET
  destination or `/profile`; setup/auth/mutation/external destinations are rejected.
  Completion requires name, age 18–120, location, and housing situation, not just
  an account or profile row. See the profile guide for the full redirect contract.
- `/profile` and `/preferences` redirect anonymous visitors to login with a local
  `next` destination. `/profile` is a read-only saved overview, `/profile/setup`
  handles onboarding, and `/profile/edit` provides a prefilled editor using the
  existing `/profiles` API. `/preferences` shows saved lifestyle preferences and
  `/preferences/edit` provides its prefilled editor. See the lifestyle section below and
  [profile integration](../docs/profile-integration.md) for migration, field mapping,
  completion rules, browser tests, and manual checks.
  `/find-roommates` and `/roommate/<profile_id>` now render real matching/profile
  API results. See [matching integration](../docs/matching-integration.md).
  Protected `/matches`, `/profiles/...`, and `/interest/...` APIs keep their
  existing checks and behavior.

## Show Interest and My Matches

Roommate details send/withdraw interest through the existing `/interest/<user_id>`
API using authenticated cookies and CSRF. My Matches is available in the account
dropdown at `/my-matches`, with Mutual Matches, Interests Sent, and Interests
Received. State is refreshed from SQLite-backed APIs, and mutual confirmation
requires the mutual endpoint's data. No interest algorithm or schema was changed.
See [the interest guide](../docs/interest-integration.md) for exact behavior and tests.

## Lifestyle preferences (Step 9)

`/preferences` is a protected, read-only overview with one white card, divided
sections, and one red **Edit preferences** action. On a first visit, it shows the
available choices and actual unset values. `/preferences/edit` is the prefilled
editor; Save uses the real authenticated `PUT /preferences/me`, then returns to
the overview with a server-confirmed success message. Cancel returns without
saving. An empty choice is JSON `null`, never an invented default.

| Field | Frontend values → labels |
| --- | --- |
| cleanliness | null → No preference; relaxed → Relaxed; moderate → Moderate; very_clean → Very clean |
| sleep_schedule | null → No preference; early → Early sleeper; late → Night owl; flexible → Flexible |
| study_habits | null → No preference; quiet → Quiet; social → Social; mixed → A mix of both |
| smoking_preference | null → No preference; non_smoking → Non-smoking; smoking_ok → Smoking is okay |
| pet_preference | null → No preference; no_pets → No pets; pets_ok → Pets are okay |
| budget | null → No budget set; otherwise a nonnegative whole-dollar integer, including zero |

### API integration and PR #12

The current branch already contained the `preferences` table, but had no
preferences API or blueprint registration. Only `app/preferences.py` and its
focused tests were brought over from
[Stuti's PR #12](https://github.com/Thewhitesoul/Roomie/pull/12), branch
`stuti-database-implementation`, head
`54d9dcfb0173d1aa9e747d099a22eafc7e90ce7b`. The local remote-tracking ref matched
the PR head when inspected. The factory adds only the import and registration
for this blueprint, preserving the newer app factory, templates/assets, CSRF,
all other blueprints, and `/health`.

- `GET /preferences/me` returns `{user_id, cleanliness, sleep_schedule,
  study_habits, smoking_preference, pet_preference, budget}`. It returns null
  fields when no row exists and does not create a row during GET.
- `PUT /preferences/me` accepts a JSON object. It upserts the authenticated
  user's row, preserves fields omitted from a partial update, and clears values
  explicitly set to null. Ownership comes only from `g.user`; `id`, `user_id`,
  and unknown fields are rejected. Text is trimmed, nonempty, at most 100
  characters, and cannot contain control characters. Budgets must be integer
  values from 0 through 9223372036854775807; booleans, floats, strings, negative
  values, and overflow are rejected. Invalid/non-JSON input returns 400.
- The HTML overview/editor reuse the exact registered GET API handler on the
  server, following discovery's existing pattern. This provides SQLite values
  on first render and preserves full integer precision. JavaScript serializes
  validated whole-dollar input without rounding through `Number`, submits PUT
  with cookies and the existing CSRF header, and displays actual API errors.
  The imported save handler's only adaptation is a success flash after a
  completed write, matching the existing profile flow.
- Saved free-text values outside the suggested dropdown choices remain visible
  and get a selected saved-value option in the editor. They are never silently
  cleared or replaced. Labels and saved values are escaped; no user HTML is used.

No PR merge was attempted and there are no unresolved Git merge conflicts. The
PR's broader changes remain unintegrated and need manual review: its form-based
auth/password-hashing changes overlap the newer JSON-only, CSRF-protected login;
its optional age validation differs from the existing required 18–120 age and
housing onboarding; and its factory/schema changes must retain the current
frontend setup and non-destructive profile migration. Those files were not
replaced. The imported persistence test was adjusted to use JSON logout and a
real CSRF token for login into a fresh app. The existing authentication browser
test now asserts the functional preferences overview instead of a preview form.

### Budget overlap and database compatibility

**For Stuti and Arpan:** `profiles.budget` and `preferences.budget` are separate
fields. Saving either does not synchronize or overwrite the other. Discovery's
existing budget filters still use **profiles.budget**; lifestyle values are not
automatically part of the matching algorithm. The team must decide which budget
the final product should use before consolidating these fields or changing
matching. This integration makes neither decision.

No schema changes or database replacement are needed. The current development
SQLite file already has all seven preference columns. If an older database is
missing this table, the existing `flask --app app init-db` safely creates missing
tables without deleting records. The existing profile migration remains intact.
Saved preferences persist in the same SQLite file after a Flask restart; normal
session expiration may require login again. No browser or JSON-file storage is
used. Auth, profile saving, matching, interests, and notification logic are retained.

### Lifestyle preferences on roommate profiles

`/roommate/<profile_id>` displays **Lifestyle preferences** below Interests inside
the existing white profile container. It uses the authenticated, read-only
`GET /preferences/profile/<profile_id>` endpoint's registered handler, never
`GET /preferences/me` to read another person's settings. The lookup joins the
profile's owner to their existing SQLite preferences row using **profile ID**.

This endpoint returns exactly six fields: cleanliness, sleep_schedule,
study_habits, smoking_preference, pet_preference, and budget. It returns no user
ID, email, password, session data, or other account metadata. GET responses use
`Cache-Control: no-store`; unauthenticated requests return 401, missing profiles
return 404, and write methods are unavailable. The existing owner-only PUT and
CSRF rules are unchanged.

An existing profile with no preferences returns six nulls without creating a
row. The detail page shows **Not specified** for unset values; it never substitutes
the viewer's preferences or `profiles.budget`. Saved values use the same dropdown
labels as the editor, custom text is escaped, zero budgets remain zero, and
large SQLite integers retain precision. Reloading the profile shows newly saved
settings. Preference-read errors leave the profile/interest controls available
and show a retry message instead of a fabricated empty state.

The Preferences editor now states that all six lifestyle settings, including
the preference budget, are visible to other logged-in Roomie users. Settings on
someone else's profile have no editor or mutation controls.

Manual verification: use two independent signed-in browser sessions. Save all
six fields as A, then view A's `/roommate/<profile_id>` as B. Confirm the lifestyle
section follows Interests, uses A's values (even if B has different settings),
and contains no private account data or edit controls. Update A's settings and
reload B's view; check a profile with no settings, a zero/blank budget, and mobile
widths. Log out as B and verify both the page and sharing API require login.

Run `pytest src/roomie/tests/test_shared_preferences.py -q` for the focused
sharing/security tests. The complete Chrome runner includes two-session sharing,
save/update, missing-value, safe text, and desktop/mobile scenarios alongside all
earlier feature checks.

### Preference verification

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest src/roomie/tests/test_preferences.py src/roomie/tests/test_preferences_frontend.py -q
.venv/bin/python tests/browser/run_profile.py
node --check src/static/preferences.js
node --check tests/browser/preferences.mjs
```

The focused API/HTML tests cover empty state, all six fields, partial updates,
nulls, validation, safe custom values, CSRF, account isolation, and persistence
through a fresh Flask app using the same database. Repeated `init-db` also
preserves accounts, profile IDs, profile data, interests, and preferences.
Chrome checks add real Save/Edit/Cancel, refresh/login persistence, mobile
layouts, 64-bit budgets, server/network errors, and independent user sessions.
Current final-audit results: **395 active pytest tests passed**, including
**44 owner-preference tests** and **18 sharing tests**; **64 Chrome scenarios passed**,
including all 61 previous scenarios and three final-audit regressions. Desktop and
mobile screenshots were inspected. The first imported API test run exposed an
outdated non-JSON logout call in its persistence test; adapting that test to the
existing JSON/CSRF contract fixed it. Final runs have no failures.

Manual checks with the backend running:

1. Sign in and choose Preferences from the account dropdown. A new account
   should show No preference values and the available choices, with no editable
   form until you choose Edit preferences.
2. Set all five lifestyle choices and an optional whole-dollar budget. Save;
   verify the success notice, read-only labels, and saved amount. Reload, edit,
   and confirm all six fields are prefilled.
3. Change values and choose Cancel. Verify nothing changed. Save No preference
   choices and a blank budget to clear them; separately verify zero is retained.
4. Compare My Profile's budget before/after saving preferences. It must stay
   unchanged, as must roommate discovery results and filters.
5. Log out/in, then stop/start Flask with the same database and sign in again.
   Confirm the values persist. Use another browser/incognito account to verify
   that preferences remain isolated.
6. Try negative/fractional budgets and a missing/wrong CSRF header. Invalid
   requests must not change data. Block `/preferences/me` while saving to check
   network feedback and retained edits, then unblock and retry. Confirm anonymous
   API requests fail and private pages redirect to login.
7. Repeat overview/edit/cancel at 1440px, 768px, and 360px. Verify the single card,
   keyboard-operable controls, account menu, notification panel, and existing
   Show Interest/My Matches workflows.

## Session and CSRF settings

Session cookies default to `HttpOnly`, `SameSite=Lax`, and `Secure`. Production
must use HTTPS, a stable random `SECRET_KEY` shared by all workers, and must not
set `ROOMIE_COOKIE_SECURE=0`. `instance/config.py` can override Flask settings.
Without `SECRET_KEY`, a random process-local development key is generated; it
invalidates sessions on restart and is unsuitable for multiple workers.

A random synchronizer token lives in the signed session. HTML pages embed it in
`<meta name="csrf-token">`; API clients can bootstrap with `GET /auth/csrf` using
a cookie jar. Every POST/PUT/PATCH/DELETE must send it as `X-CSRF-Token`, including
registration, login, logout, and existing cookie-authenticated mutation APIs.
Missing, wrong, cross-session, or stale tokens return JSON 403 before mutation.
Session clearing on registration/login/logout invalidates old tokens; the next
page/API bootstrap creates a fresh one. On a stale-tab 403, reload before retrying.
HTML and JSON API responses use `Cache-Control: no-store`. No CORS access is added.
Cookie flags complement token validation; they do not replace it. See the
[Flask security documentation](https://flask.palletsprojects.com/en/stable/web-security/).

## Verification

From the repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest src/roomie/tests/tests_auth.py -q
node --check src/static/app.js
git diff --check
```

`pytest.ini` collects all active frontend/backend tests, including the previously
undiscovered `tests_auth.py`. The two legacy sources in `not required anymore/`
were removed locally before the final audit. Active imports/tests do not depend
on them; no JSON-file storage is used. Include those intended deletions when
the integration is eventually committed. See the current
[integration audit](../docs/code-and-tests.md) for final results and merge gates.

The shared API test client obtains real CSRF tokens; protection is never disabled
in tests. Adversarial browser-contract tests use a raw client to verify missing,
wrong, cross-session, stale, and malformed tokens, malformed JSON and field types,
password confirmation, actual SQLite accounts/hashes, redirects, cookie flags,
page guards, and navigation across registration/login/logout.

Manual browser checks (backend running as above):

1. Open `/` in a private window. Verify Home, Find roommates, Log in, Get started;
   no account dropdown. Open `/profile` and `/preferences` directly and verify a
   redirect to `/login?next=...`.
2. Open `/register`. Try a 7-character password and mismatched confirmation; the
   browser should prevent submission. Use a unique username/email and matching
   password of at least 8 characters. Verify redirect, success message, and your
   username in the account dropdown before setup, then your chosen display name
   after completing setup; Log in and Get started should disappear.
3. Open the menu by click/tap and Enter/Space. Tab through links, press Escape,
   click outside, and check at 360px, 768px, and desktop widths. Preferences and
   My Profile should load real saved data.
4. Log out through the menu. Verify the success notice, logged-out navigation,
   `/auth/me` returning 401, and private-page redirects. Register the same email
   or username again and verify the actual duplicate-account error.
5. Open `/preferences` while logged out. Try an incorrect password, then log in
   correctly. Verify the real error followed by a redirect back to `/preferences`.
6. In DevTools Console, run
   `fetch('/auth/logout', {method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'}).then(async r => console.log(r.status, await r.json()))`.
   Expect 403; reload and verify you remain signed in. Check Network requests for
   JSON credentials and `X-CSRF-Token`, and verify localStorage contains no auth
   material. Test production cookie flags separately over HTTPS.

## Standalone visual preview

`python -m flask --app src.preview run` from the root remains a separate,
unauthenticated visual preview. Login/registration there still show preview
feedback and make no network requests. Use the backend run command for the real
workflow. Matching, My Profile, and Show Interest/My Matches are connected in the
backend app, alongside the lifestyle preferences described above. See [interest integration](../docs/interest-integration.md)
for connection state, two-session tests, and manual verification. The standalone preview shows no real or fictional
roommate results and never accesses protected APIs. Backend profile/matching/interest
logic are unchanged. The schema adds only the two nullable onboarding profile
columns described in the profile guide.
