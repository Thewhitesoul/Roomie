# Saved profiles and onboarding

> This feature guide records its implementation-stage checks. For current setup,
> full test counts, known limitations, and merge readiness, use the
> [final integration audit](code-and-tests.md).

The backend app now provides three authenticated pages:

- `/profile/setup`: onboarding for a missing/incomplete profile, prefilled with
  every saved value. Includes **Save and continue** and **Finish later**.
- `/profile`: read-only overview with an initial avatar, display name, account
  username, personal information, housing/budget, interest tags, and biography.
- `/profile/edit`: the same prefilled form in edit mode, with **Save changes**
  and **Cancel**. Cancel is a GET link and never submits a mutation.

The bright blue/red palette, rounded surfaces, glass navigation, and accessible
account dropdown are retained. The account button uses the saved display name,
falling back to the login username when no display name is present. No photo
uploading or private account editing is introduced. Email/password data is never
included in public roommate profile serialization or templates.

## Completion and redirects

`app/profile_state.py` defines completion from the actual SQLite row:

- A nonblank display name, at most 60 characters.
- An integer age from 18 through 120.
- A nonblank preferred location, at most 100 characters.
- `housing_status` of `needs_housing` or `has_housing`.

Account existence alone is never sufficient. Bio, interests, and budget are
optional and do not block completion.

Registration still uses the existing `/auth/register` API, password hashing,
signed session, and CSRF. Its current preview-only template was reconnected to
that handler, with named password fields and the existing 8-character password
minimum. Successful registration authenticates the user and returns
`/profile/setup`. Login returns setup for an incomplete row, and otherwise a
safe intended destination or `/profile`. A completed user visiting setup is
redirected to the overview, never into a setup loop.

Intended destinations are allowlisted local GET pages: home, profile, profile edit,
preferences, matching, and numeric roommate-detail URLs. Only matching accepts
query parameters, retaining filter destinations. External URLs, protocol-relative
URLs, backslashes, control characters, auth/mutation routes, and setup itself
are rejected. An incomplete user's safe destination can be retained in the
existing signed session and consumed once after setup succeeds. With no intended
destination, Save returns to the saved overview.

## Existing profile API

There is one profile store and one profile API: `POST /profiles`,
`GET /profiles/me`, and `PUT /profiles/me`. Setup/edit read the saved profile before
enabling Save. A missing row uses POST; existing rows, including incomplete
legacy profiles, use PUT. Successful saves return to the overview with a real
server flash message. Client fields and IDs never establish ownership; the API
always uses `g.user['id']`. A duplicate create returns 409, including when the
existence check races another request. The UNIQUE constraint prevents duplicate
profiles, and the profile/interest creation write is atomic.

| UI field | JSON field | Validation |
| --- | --- | --- |
| Display name | `name` | Required, trimmed, maximum 60; independent of login username |
| Age | `age` | Required integer, 18–120; booleans/fractions/strings rejected by API |
| Preferred location | `preferred_location` | Required, trimmed, maximum 100 |
| Housing situation | `housing_status` | Required, `needs_housing` or `has_housing` |
| Interests | `interests` | Comma input becomes trimmed nonempty strings; maximum 10, 30 characters each |
| About me | `bio` | Optional, maximum 500 |
| Monthly budget | `budget` | Optional `null`, or whole nonnegative dollars, including zero |

New POSTs require the four completion fields. PUT remains a partial update,
validating provided fields while retaining omitted values. An incomplete legacy
row is readable and can be completed without changing its ID. Clearing optional
bio/interests/budget is supported. Existing interest lowercase/deduplication
behavior is retained. There is no CSV escaping for an interest containing a comma.

All mutations use the existing same-origin session cookies and `X-CSRF-Token`.
A stale/missing token returns 403; an expired session returns a login-required
response. Failed loads disable saving until Retry succeeds. Failed saves retain
entered values. JavaScript is required for API form submission; the overview is
server-rendered. No localStorage, JSON-file storage, or fake success flags are used.

## Non-destructive SQLite migration

Two nullable columns are added to `profiles`:

```sql
age INTEGER CHECK (age IS NULL OR (typeof(age) = 'integer' AND age BETWEEN 18 AND 120))
housing_status TEXT CHECK (housing_status IS NULL OR housing_status IN ('needs_housing', 'has_housing'))
```

Nullable storage deliberately preserves existing incomplete rows without
inventing ages or housing situations. Application completion rules and new-profile
validation require real values. `schema.sql` includes the columns for new databases.
`db.migrate_profiles()` handles existing databases with additive `ALTER TABLE`
statements in one transaction, not just `CREATE TABLE IF NOT EXISTS`. It never
rebuilds/drops a table or rewrites user/profile IDs, interests, requests, or
preferences. It rechecks columns under a write lock, is idempotent, supports a
partially upgraded database, and rolls back if any addition fails.

Normal first database access automatically applies pending additions. For an
explicit upgrade before serving traffic, take a SQLite backup and run from
`src/roomie` with the existing configured database:

```bash
python -m flask --app app migrate-db
```

For a new installation, use `python -m flask --app app init-db`; initialization
also handles old tables safely and does not erase data. Do not delete the existing
database or recreate tables to obtain the columns. The tests and browser checks
use temporary databases; this work does not manually migrate the development file.

Matching/ranking and mutual-interest logic are unchanged. The profile GET
serialization now includes age/housing, and public detail pages display these
only when actually provided. Preferences remain pending. Show Interest/My Matches
are connected separately; see [interest integration](interest-integration.md).
The single-card My Profile overview and its editing flow are preserved.

## Verification

From the repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest src/roomie/tests/tests_auth.py src/roomie/tests/test_profile_onboarding.py -q
.venv/bin/python tests/browser/run_profile.py
node --check src/static/app.js
node --check tests/browser/profile.mjs
git diff --check
```

`test_profile_onboarding.py` checks completion-based registration/login redirects,
safe intended paths, loop avoidance, legacy prefilling, read-only overview,
edit/cancel, validation, duplicate-create races, account isolation, CSRF, fresh and
migrated SQLite constraints, transactional rollback, exact preservation of all
old table values, and ID-sequence continuity. Existing profile tests cover a fresh
Flask app using the same SQLite file after restart. Matching/interest fixtures now
provide the required fields; their algorithms were not changed.

The Chrome runner uses a temporary SQLite database and real APIs with CSRF enabled.
It also seeds one explicitly incomplete legacy row to test recovery; this is test
fixture data, never a production fallback. It checks setup, overview, edit/cancel,
validation, expired sessions, CSRF failures, GET failure/retry, completed logins,
legacy completion, navigation keyboard behavior and responsive layouts, plus the
existing matching scenarios. Requires Node with built-in WebSocket and Chrome;
set `ROOMIE_CHROME_EXECUTABLE` if needed. Only its loopback HTTP test server disables
Secure cookies. The desktop/tablet/mobile overview captures are written as
`roomie-profile-overview-{1440,768,360}.png` in the OS temporary directory.

## Manual browser verification

1. Start the backend from `src/roomie`:
   `ROOMIE_COOKIE_SECURE=0 python -m flask --app app run --debug --port 5002`.
   Use that cookie override only for local HTTP, not production HTTPS.
2. In a private browser, visit `/profile/setup` and `/profile/edit`; both must
   redirect to login. Register a unique account at `/register`. Confirm successful
   authentication and immediate `/profile/setup`, with no pre-created fake profile.
3. Enter a display name distinct from the username, age 18–120, location, housing
   choice, optional whole-dollar budget, interests such as `Cooking, , Hiking`,
   and a bio. Save and continue. Confirm `/profile` shows read-only sections,
   your initial avatar, actual saved values, and your display name in the menu.
4. Reload. Click Edit profile, verify every field is prefilled, change values,
   then Cancel. Confirm the overview and GET `/profiles/me` remain unchanged.
   Edit again, save, and verify updated values plus a success message. Check that
   the existing profile ID is retained and edits use PUT rather than another POST.
5. Log out and log in again with the completed account. Expect `/profile`, not
   setup. Try `/login?next=/find-roommates?location=Topeka` and confirm that safe
   filter destination. Try an external `next`; it must not redirect off-site.
6. Use an existing incomplete account after migration. Login must open setup with
   all old values (including interests, bio, and budget zero) retained. Fill only
   missing required information; save and confirm the same profile ID. Later
   logins must skip setup. Restart the app and confirm saved data persists.
7. Validate empty required fields, ages 17/121/fractions, a fractional or negative
   budget, 11 interests, a 31-character interest, and a bio over 500 characters.
   Native/API errors must not overwrite saved data or erase edits. In DevTools,
   replace the CSRF meta token with `invalid` and attempt Save: expect 403 and
   unchanged saved data; reload to obtain a valid token.
8. Check overview and edit at 360px, 768px, and desktop widths. Open the account
   menu by click or Enter/Space, Tab through links, and close with Escape/outside
   click. Verify public roommate details contain no email/password information.
