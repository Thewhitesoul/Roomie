# Show Interest and My Matches

> This feature guide records its implementation-stage checks. For current setup,
> full test counts, known limitations, and merge readiness, use the
> [final integration audit](code-and-tests.md).

Roommate details at `/roommate/<profile_id>` now load the viewer's actual
relationship state. Show Interest uses `POST /interest/<user_id>`, and Withdraw
interest uses `DELETE /interest/<user_id>`. Both send same-origin session cookies
and the existing `X-CSRF-Token`. Profile IDs are never substituted for user IDs.
A user's own profile has no interest action.

The account dropdown links to the authenticated `/my-matches` page. Its three
sections consume the existing APIs directly:

| Section | API | Meaning |
| --- | --- | --- |
| Mutual Matches | `GET /interest/mutual` | Both users have sent interest |
| Interests Sent | `GET /interest/sent` | Your outgoing interests |
| Interests Received | `GET /interest/received` | Incoming interests from others |

A mutual connection naturally appears in all three views. There is still only
one directed interest row per sender/recipient pair, as enforced by the existing
SQLite UNIQUE constraint. The frontend does not calculate a second matching
algorithm: mutual banners and badges come from the mutual API, never just from
an outgoing interest. Existing backend endpoints, SQL, schema, discovery ranking,
authentication, profile saving, and the single-card My Profile layout are retained.

## In-app connection notifications

Authenticated backend pages include a bell with a **pending incoming interests**
count. The panel lists received interests whose user IDs are absent from your
sent interests (and excludes confirmed mutual matches). It shows mutual matches
separately, using only `GET /interest/mutual` as positive confirmation. Names
fall back to actual usernames; links use profile IDs. Accounts without profiles
get an explicit unavailable message. No private email/password fields are used.

The homepage, saved profile, and other authenticated pages show an **It's a
Match!** announcement when confirmed mutual matches exist, linking to My Matches.
Roommate details and My Matches retain their existing context-specific banners
instead of receiving a second announcement. These are current relationships,
not unread or newly received notifications: no read state is tracked or implied.

Notifications refresh on page load, focus, visible-tab return, back/forward cache
restoration, manual Refresh, and successful/conflicting interest mutations. While
the page is visible, a 60-second timer also checks the three existing APIs.
Concurrent notification reads are coalesced, a mutation queues a fresh read, and
requests time out after 15 seconds. Polling does no work in hidden tabs and stops
on page exit or an expired session. There are no WebSockets or background services.

Confirmed notification snapshots also update an idle My Matches/detail view, so
a withdrawn mutual match does not leave an old card or banner visible after a
notification refresh. API failures clear notification counts and lists rather
than presenting a fabricated zero; 401 responses clear private connection views
and offer login. Page exit clears notification data before cached restoration.
All rendering uses text nodes. No browser storage, extra API, SQLite schema,
authentication, or profile-saving change is involved.

The disclosure uses a native button with expanded/controls attributes, supports
Enter/Space, arrow keys, Tab, Escape with focus restoration, and outside clicks.
The panel becomes part of the navigation flow at mobile widths.

## State, errors, and rendering

- Buttons remain disabled until fresh API data is available. During a mutation,
  all connection actions on that page are disabled and a busy/live status is shown.
  The synchronous guard also prevents double clicks across duplicate card views.
- After sending, the main button reads **Interest sent** and disables sending;
  **Withdraw interest** becomes available. Sending back from Interests Received
  uses the same API and may create a real mutual match.
- A POST 409 triggers fresh reads instead of another POST. A DELETE 404 similarly
  reconciles an already-withdrawn interest. No blind automatic mutation retries
  are made. Successful writes followed by failed reads say that the change was
  saved but status needs refreshing; they do not claim an unverified mutual match.
- Every mutation refreshes the lists and confirmation. Withdrawal removes a mutual
  connection from mutual/sent while preserving any incoming interest that still
  exists. The other user's view updates when refreshed or revisited.
- State refreshes on page load, browser back/forward cache restoration, focus, and
  returning to a visible page. Explicit Refresh controls are also available.
  The notification controller adds visible-page polling as described above.
- GETs use `cache: 'no-store'`. There is no localStorage relationship state or JSON
  file storage. SQLite remains the sole persistent application data store.
- Missing/invalid CSRF returns the existing 403 error without a write. Reload for
  an expired token. A 401 clears rendered private lists and offers a safe login
  link. `/my-matches` is included in the existing local redirect allowlists.
- Errors are not rendered as empty lists. Confirmed empty responses have helpful
  empty states; loading and failed reads have their own feedback and retry path.
- Cards display only available name, username, and API timestamps. SQLite timestamp
  strings are interpreted as UTC and formatted for the browser. Missing names use
  the actual username; missing dates are omitted. Profile links use `profile_id`.
  A null profile ID shows **Profile not available yet**, without an invented link.
- Names, usernames, errors, and timestamps use DOM textContent/text nodes, never
  untrusted HTML. The APIs already omit email/password fields, and cards never
  introduce those fields. No additional personal information is fetched.

JavaScript is required to load relationship data and send/withdraw interest.
Without it, the pages explain this and keep mutation controls disabled. No fake
success state is provided. The standalone visual preview remains unauthenticated
and does not gain live interest actions.

## Changed files for this feature

- `src/roomie/app/frontend.py`: protected My Matches HTML route.
- `src/roomie/app/profile_state.py`, `src/static/app.js`: allow the new local
  read-only destination after login, retaining existing redirect safeguards.
- `src/templates/base.html`: page-script block and authenticated dropdown link.
- `src/templates/profile_detail.html`: live action, mutual confirmation, and self guard.
- `src/templates/my_matches.html`: the three connection sections and loading/error UI.
- `src/static/interests.js`: API reads/mutations, safe rendering, synchronization,
  CSRF headers, and keyboard focus restoration.
- `src/static/style.css`: scoped connection styles and responsive layouts.
- `src/roomie/tests/test_interest_frontend.py`: separate-session API/HTML tests.
- `src/roomie/tests/test_matching_frontend.py`: replace the old pending-action expectation.
- `tests/browser/profile.mjs`, `tests/browser/interests.mjs`: retain existing browser
  regressions and add two isolated browser-context tests using real cookies/APIs.
- This guide and the README/profile/matching guides.

No new schema or migration is needed. `app/interests.py` is unchanged.

Notification-only additions/changes:

- `src/templates/base.html`: authenticated bell/panel and shared match announcement.
- `src/static/notifications.js`: current pending/mutual state, safe rendering,
  disclosure behavior, refresh lifecycle, and confirmed API snapshots.
- `src/static/interests.js`: mutation events and reuse of notification snapshots.
- `src/static/style.css`: scoped bell, panel, and announcement styles.
- `src/roomie/tests/test_notifications.py`: authenticated rendering, read-only
  page behavior, source records, withdrawals, and account isolation.
- `tests/browser/notifications.mjs`: real two-session notification checks;
  `profile.mjs` runs them and `interests.mjs` waits for initial notification reads
  before intentionally exercising stale-state conflicts.
- This guide: notification semantics, verification, and browser steps.

## Automated verification

From the repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest src/roomie/tests/test_interest.py src/roomie/tests/test_interest_frontend.py src/roomie/tests/test_notifications.py -q
.venv/bin/python tests/browser/run_profile.py
node --check src/static/notifications.js
node --check src/static/interests.js
node --check src/static/app.js
node --check tests/browser/interests.mjs
node --check tests/browser/notifications.mjs
git diff --check
```

Final full-suite result: **299 passed**; focused interest/notification tests:
**45 passed**. Final Chrome result: **41 scenarios passed**,
including existing registration/login, onboarding, single-card profile/edit/cancel,
and matching/filter checks. The interest scenarios use two independent Chrome
browser contexts with distinct cookie jars, plus actual SQLite records in a
temporary database. They exercise user/profile ID separation, one-way interest,
mutual confirmation, withdrawal on both sides, 409/404 reconciliation, CSRF, invalid
IDs, profile-less users, private-field safety, HTML injection, loading failures,
session expiry, and layouts at 1440px, 768px, and 360px. API tests also verify
persistence in a fresh Flask app using the same SQLite file. Ten notification
scenarios verify counts, incoming profile links, mutual announcements outside
roommate details, returning to the site, local and remote withdrawals, keyboard
controls, missing profiles, hostile names, API errors, session expiry, and account
isolation. Notification layouts were checked at 1440px, 900px, 768px, and 360px;
desktop/mobile screenshots were also visually inspected.

The notification browser checks initially caught a test selector collision
between the badge and its parent's count attribute; distinct attributes fixed it.
Review also caught a stale My Matches card after a notification-only refresh;
shared confirmed snapshots fix it and browser checks cover it. Final tests pass
without disabling CSRF or modifying development data. The minute-long polling
interval is not elapsed in the automated scenarios; page-load, focus, manual,
and post-mutation refreshes are exercised directly.

## Manual browser verification

1. Start the existing backend from `src/roomie`:
   `ROOMIE_COOKIE_SECURE=0 python -m flask --app app run --debug --port 5002`.
   Use that cookie override only for local HTTP. Sign in to completed account A
   in a regular window and account B in an incognito window or another browser.
2. As A, find B through Find roommates and open B's profile. Click Show Interest.
   Confirm **Interest sent**, the Withdraw option, and no mutual confirmation yet.
   Reload or leave and return; state must persist. Network should show POST to
   B's `user_id`, not B's `profile_id`, with the CSRF header.
3. As B, open My Matches from the account menu. A should appear under Interests
   Received. Use Show Interest on A's card. Confirm **It's a Match!** and a mutual
   card. Refresh A's page and verify the same mutual relationship.
4. Open My Matches as A. Verify names/usernames, dates, correct profile links, and
   the Mutual/Sent/Received views. Withdraw interest. A's Sent/Mutual entry should
   disappear while B's incoming interest remains. Refresh B: mutual must be gone,
   but B's outgoing interest should remain until B withdraws it.
5. Test rapid repeated clicks, reloads, and a second tab with stale state. Duplicate
   sends must resolve without duplicate rows. Empty categories should explain
   their state instead of showing example people.
6. In DevTools, replace the page's CSRF meta token with `invalid` and try an action.
   Expect 403, visible feedback, and no database change; reload to obtain a valid
   token. Block `/interest/sent` and refresh to test loading errors, then unblock
   and use Refresh. Log out in another tab, refresh, and confirm login guidance.
7. Repeat at 360px, 768px, and desktop widths. Tab to actions and activate with
   Enter/Space; verify the dropdown still supports Escape/outside click. An account
   without a profile should have no fabricated profile link. Roommate cards must
   contain no private email or password details.

## Manual notification workflow

1. With completed accounts A and B signed in using separate browser sessions,
   leave A on My Profile. As B, open A's roommate profile and send interest.
2. Return focus to A's window or open Notifications and choose Refresh. Expect
   one pending incoming interest, B's real display name/username, a link to B's
   profile, and no mutual-match announcement. Opening the panel does not mark
   anything read or remove a pending interest.
3. As A, open B's profile from that notification (or use My Matches) and show
   interest back. Expect zero pending interests for that relationship and a real
   mutual match. Leave B on My Profile and return focus to B: **It's a Match!**
   appears without visiting A's profile. Reload the homepage and check it again.
4. Open My Matches in both sessions. Withdraw A's interest. A should have one
   pending incoming interest from B; B should have no pending interest from A.
   After focus/Refresh, both mutual banners/cards disappear. Withdraw B's
   remaining interest and confirm both pending counts are zero.
5. Leave a recipient's page visible while the other browser sends interest.
   Without focusing or refreshing that recipient page, wait up to 60 seconds
   (plus request time) for polling. Hide the tab and confirm no periodic interest
   reads occur there; return to it and verify an immediate refresh.
6. At desktop and mobile widths, use Enter/Space to open the bell, Tab through
   links/Refresh, Escape to close and restore focus, and click outside to close.
   Log out in another tab and refresh notifications: names/counts must clear and
   login guidance must appear. The other browser's session must remain isolated.
