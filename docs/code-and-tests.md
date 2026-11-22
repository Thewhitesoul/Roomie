# Roomie integration audit and code/test reference

Audit date: 2026-11-20. Scope: the **local working tree** on
`feature/frontend-backend-integration`, including uncommitted and untracked work.
The remote branch is not a substitute for this checkout.

## A. Readiness

**Ready for local MVP team testing.** Main-branch merge is gated on reviewing and
including the complete local change set, resolving PR #12's scope, and team
sign-off. No commit, push, merge, branch deletion, or destructive database change
was performed by the audit. This is not a production deployment approval.

## B. Changes made during Step 10

- Validated numeric match filters before integer conversion/SQLite binding;
  unsupported numeric characters and overflow now return 400.
- Bounded integer URL length before conversion and checked SQLite ID ranges in
  the affected API views. Invalid profile/interest/preference IDs return 404.
  Valid endpoint names and profile-ID/user-ID semantics are unchanged.
- Rejected overflowing profile budgets before writes and preserved exact budget
  tokens through profile form loading/saving. Ordinary budgets and the full
  SQLite integer range round-trip without JavaScript Number rounding.
- Applied `Cache-Control: no-store` to HTML and JSON responses, leaving static
  asset caching intact.
- Added portable ignore rules for `.venv-*`, `.env.*`, and SQLite sidecars;
  `.env.example` remains eligible for intentional tracking.
- Pinned direct requirements to the versions already tested locally; no package
  upgrade or dependency installation was performed.
- Added 34 audit regressions, strengthened the fresh CLI initialization test,
  and added three real Chrome scenarios. No existing assertions were removed.
- Updated root/source setup instructions and this formerly stale reference.

Affected source: `app/__init__.py`, `db.py`, `profile.py`, `matches.py`,
`interests.py`, `preferences.py`, `security.py`, `static/app.js`, and
`templates/profile_form.html`. Matching selection/ranking and the SQLite schema
were not changed. The simplified notification UI was retained.

## C. Defects and disposition

| Finding | Severity | Result |
| --- | --- | --- |
| Superscript numerals and extremely long numeric filters caused ValueError/500; out-of-range budgets/IDs caused SQLite OverflowError/500 | Medium | Fixed with controlled 400/404 responses and data-preservation regressions |
| Profile editor rounded large SQLite integer budgets via JavaScript Number, potentially changing a saved amount on a later edit | Medium | Fixed and tested above Number.MAX_SAFE_INTEGER and at SQLite's maximum |
| Private JSON endpoints lacked an explicit server no-store policy (browser controllers already used no-store reads) | Low, defense in depth | Fixed; authenticated JSON cache headers tested |
| Root setup guide described an unimplemented project; old test reference claimed 85/87 tests and destructive init-db | Low, documentation | Corrected to current setup, non-destructive initialization, and results |
| Numbered virtual environments relied on their own ignore files; dotenv variants and SQLite sidecars were not covered by repository rules | Low, hygiene | Fixed; no generated files or detected token/private-key signatures were tracked |

Baseline full suite: **361 passed, 0 failed**. Extra audit probes reproduced nine
uncaught numeric-error paths not covered by that baseline. An initial new-test
run reported **44 passed, 1 failed** because range rejection in the URL converter
produced DELETE 405 instead of the asserted 404. Range checks were moved into
the existing authenticated views; the unchanged regression assertions then
passed (**45 passed, 0 failed** including database tests).

No unresolved critical or major MVP workflow defect was observed. The existing
API quirk that `limit=0` uses the default limit was preserved rather than changing
matching behavior during an audit.

## D. Python verification

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest src/roomie/tests/test_integration_audit.py src/roomie/tests/test_db.py -q
```

- Final complete active suite: **395 passed, 0 failed** (58.36 seconds).
- Focused audit/database regressions: **45 passed, 0 failed**.
- Existing profile/matching/sharing tests also ran separately: **61 passed**.
- `pytest.ini` includes both `tests/` and `src/roomie/tests/`, explicitly discovering
  `tests_auth.py`. The removed legacy JSON-storage tests are not active tests.
- No CSRF check, login guard, or validation assertion was disabled to obtain these
  results. The fresh CLI test now verifies actual tables and data retention.

## E. Browser and runtime verification

```bash
.venv/bin/python tests/browser/run_profile.py
```

**64 Chrome scenarios passed, 0 failed**, covering all 61 prior scenarios plus
profile-budget precision, controlled numeric errors/cache headers, and the real
60-second visible-page notification timer. The polling scenario received real
incoming interest without manual refresh, synthetic focus, or fixture auth flags.

Checks include registration/login/logout, incomplete/complete-profile redirects,
profile single-card/edit/cancel, discovery filters/ranking, actual profile versus
user IDs, send/withdraw/409 reconciliation, mutual/sent/received lists, simplified
notifications, all preference fields/nulls, shareable settings, safe text, API
and network errors, CSRF rejection, expired sessions, and account isolation.
Two independent authenticated Chrome cookie jars were used.

Layouts are exercised at 1440px, 900px where applicable, 768px, and 360px. Saved
screenshots were visually inspected for the profile overview, My Matches,
notifications, preferences overview/editor, and roommate lifestyle sections. Mobile checks use
Chrome viewport/device emulation, not physical-device certification.

Additional runtime checks:

- All 11 HTML entry paths rendered/redirected safely; 16 discovered navigation,
  local link, and static asset URLs resolved successfully. No duplicate
  method/path registrations were found.
- Clean temporary database creation succeeded. An actual second Python process
  logged in and recovered the same profile, profile interests, preferences, and
  mutual-interest records without replacing/reinitializing the SQLite file.
- 500 other real SQLite test profiles, 20 authenticated filtered match requests:
  min/median/max **4.93 / 5.05 / 5.77 ms** using Flask's local test client. This is
  a small local check, not a concurrent-user or network load test.
- JavaScript syntax checks, `git diff --check`, and `pip check` passed. A no-index
  pip dry run confirmed the pinned requirements already match the environment.

Environment: macOS, Python 3.13.3, SQLite 3.49.1, Flask 3.1.3, Werkzeug 3.1.9,
pytest 9.2.0, email-validator 2.4.0, Node v24.15.0, Chrome 146.0.7680.81.
A clean network dependency install, Windows execution, and Firefox/Safari/Edge
were not performed in this audit.

## F. Database, security, structure, and limitations

- SQLite is the only persistent application-record store. JSON is API transport;
  active application code has no JSON-file storage or browser profile/auth store.
- `init-db` uses transactional CREATE IF NOT EXISTS and does not DROP tables.
  Existing profile migrations add nullable age/housing fields under a write lock;
  accounts, profile IDs, interest records, and SQLite sequences are preserved.
  Nullable legacy rows go through setup; new complete profiles require name,
  age 18–120, location, and needs_housing/has_housing.
- The development SQLite file was read only during this audit: integrity check
  returned **ok**, foreign-key violations were **0**, and its SHA256 was unchanged
  before/after testing. Automated checks used temporary databases exclusively.
- Profile budget and preference budget remain separate. Discovery filters the
  **profile** budget and ranks shared profile interests, not lifestyle settings.
- Passwords are hashed with Werkzeug; current Python supports scrypt. Stored
  PBKDF2 hashes remain readable. Registration/login clear the previous session;
  logout clears authenticated state. IDs for writes always come from the session.
- Every registered state-changing API requires the existing session-bound CSRF
  header. Owner-only profile/preferences writes, safe redirect allowlists, and
  unauthenticated page/API guards are covered by tests.
- Public roommate/profile/match payloads exclude email/password/session data.
  Shared preferences return only six allowed fields; other users cannot edit
  them. The editor discloses their visibility. DOM/Jinja rendering escapes text.
- Cookie defaults are HttpOnly, SameSite=Lax, Secure; factory debug defaults off.
  Local HTTP explicitly overrides Secure. A stable random SECRET_KEY, HTTPS,
  debug off, and a production WSGI server are required for shared deployment.
  Missing development keys are random per process, so restart requires login
  again while persisted account data survives.
- One functional application is the existing factory. `src/preview.py` is a
  separate legacy unauthenticated visual preview, retained for smoke tests and
  never used by the documented MVP launch command. There is no second functional
  auth/database stack. `feature_pending.html` is an unused legacy template, not
  a registered route. No preview/sample user is treated as authenticated.
- The two locally deleted legacy storage sources have no active imports. Existing
  generated environments/caches/databases remain ignored, not deleted. No tracked
  virtual environments, caches, SQLite files, dotenv/config secrets, or detected
  private-key/token signatures were found.
- The editor preserves full-range profile budgets on current Chrome. An older
  JSON parser lacking numeric source support refuses unsafe large-budget reads
  instead of rounding; ordinary safe-integer budgets remain supported.
- Notifications are derived current/pending relationships, not unread/new events.
  Hidden tabs skip polling; focus/load/mutation refreshes remain. There is no
  messaging, WebSocket service, read-history tracking, reset/verification flow,
  or public-deployment abuse protection. No production penetration or dependency
  vulnerability scan is claimed by this local integration audit.

## G. PR #12 review

[PR #12](https://github.com/Thewhitesoul/Roomie/pull/12) is open, targets this
branch, and has head `54d9dcfb0173d1aa9e747d099a22eafc7e90ce7b`, matching the inspected
local `origin/stuti-database-implementation` ref. Its nine changed paths were
compared with the current local implementation, not merely remote integration HEAD.
GitHub's textual mergeable flag does not account for this uncommitted work.

| PR area | Current local state / recommendation |
| --- | --- |
| Preferences API, blueprint registration, tests | Already selectively incorporated, plus shared read-only preferences, current CSRF handling, frontend, and additional tests |
| Authentication accepting HTML forms | Superseded: real forms send JSON; API intentionally rejects unsupported types and preserves CSRF/redirect behavior |
| PBKDF2-only generation to work around missing scrypt | No failure on the audited runtime; existing PBKDF2 hashes work. Recheck Stuti's affected Python build before changing hash policy |
| Optional age >=18, profile serialization/create path | Superseded by required 18–120 age, housing status, onboarding, and compatible migration; do not overwrite current profile code/tests |
| CREATE TABLE age change | Not a migration for existing files; keep the current additive age/housing migration and preferences schema |
| Factory replacement | Would lose template/static wiring, frontend routes, CSRF, and secure-session configuration if taken wholesale; preserve the local factory |
| Auth test rename/discovery and reference docs | Discovery is already fixed with pytest.ini and expanded security tests; old failure descriptions are superseded by this reference |

**Recommendation:** do not merge as-is. Preferences were already partially
incorporated. After the full local integration is reviewed and lands in the
feature branch, close #12 as superseded unless Stuti reproduces a remaining
platform hashing problem; re-scope that problem into a focused fix if needed.
Until then leave it open—the remote branch alone does not yet contain all this
work. No PR mutation/comment or merge was performed.

## H. Work before main

1. Review all modified/untracked source, tests, docs, pytest.ini, and the two
   intended legacy-storage deletions. Essential untracked integration files must
   not be omitted when the user later authorizes committing/pushing the branch.
2. Run the committed checkout on a second team machine, particularly Stuti's
   hashing environment; perform the two-user steps below and obtain team sign-off.
3. Resolve #12 using the recommendation above; preserve the complete factory,
   current profile/onboarding rules, CSRF, and ownership checks.
4. Before shared deployment, configure a stable secret, HTTPS/Secure cookies,
   debug off, database backups, and a production server. Production hardening is
   separate from this MVP audit.
5. Acknowledge the separate budgets and that lifestyle settings are not currently
   compatibility factors. Consolidation/scoring changes require a later team
   decision, not an unreviewed schema/algorithm change in this merge.

## I. Exact manual team steps

1. Follow the root README's installation instructions. From `src/roomie`, use
   `python -m flask --app app init-db` for a new database; for an existing one,
   back it up, run `python -m flask --app app migrate-db`, and use init-db only if
   tables are missing. Do not delete/replace the database to clear a test state.
2. Start local HTTP with
   `ROOMIE_COOKIE_SECURE=0 python -m flask --app app run --port 5002`.
   Open `http://127.0.0.1:5002/health` and expect `{"status":"ok"}`.
3. Use a regular browser window for A and incognito/another browser for B.
   Register distinct accounts. Reject 7-character passwords and mismatched
   confirmation; accept matching passwords of at least 8 characters. Confirm
   authenticated navigation and first-time `/profile/setup`.
4. Complete name, age 18–120, location, housing situation, optional budget/bio,
   and interests. Verify one saved white profile card and one Edit profile button.
   Edit, Cancel, reload, edit again and Save. Incomplete legacy accounts should
   return to setup; completed logins should use their safe intended destination.
5. Set all five lifestyle choices and a whole-dollar preference budget. Save,
   edit/prefill, Cancel, clear with No preference/blank budget, and test zero.
   Confirm My Profile's separate budget is unchanged. Set distinct values for B.
6. Find roommates with min/max profile budget, location, and interests. Verify
   ranking/shared interests and exclusion of your own profile. Open B's card:
   check actual name/bio/interests and B's lifestyle settings below Interests,
   not A's settings. Check an account with no preferences (Not specified), then
   edit B's preferences and reload A's view. No private email/password should show.
7. As A, Show Interest in B; refresh/revisit and confirm Interest sent plus
   Withdraw, with no false match. As B, verify Interested in you and pending count.
   Leave B's page visible while A changes interest; verify the minute poll, or
   return focus/use Refresh. Reciprocate as B; verify true match announcements
   outside details and Mutual/Sent/Received in My Matches.
8. Withdraw A's interest. Confirm mutual lists/banners disappear in both sessions
   after refresh and only B's remaining directed interest is pending. Withdraw B's
   interest and verify empty/count states. Rapid clicks must not duplicate rows.
9. In DevTools, change the CSRF meta token to invalid and attempt a save/action:
   expect 403 with no changed data. Reload to restore the token. Block an API
   request to test network feedback, unblock, and retry. Log out in a second tab;
   old tabs must not save. Logged-out API reads return 401 and private pages login.
10. Log out/in, stop/restart Flask using the same SQLite file, and log in again.
    Profiles, both budgets, lifestyle choices, and directed/mutual interest must
    persist. A's actions must never overwrite B's profile/preferences.
11. Repeat at desktop and 360px mobile width. Use keyboard Enter/Space/Tab,
    Escape and outside click for dropdowns; verify the opaque compact notification
    panel, mobile form controls, saved views, and clear errors. Record team/browser
    results before approving the main-branch merge.
