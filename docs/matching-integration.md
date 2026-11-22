# Real roommate matching UI

> This feature guide records its implementation-stage checks. For current setup,
> full test counts, known limitations, and merge readiness, use the
> [final integration audit](code-and-tests.md).

The HTML matching page is `/find-roommates` (endpoint `matches`), and details use
`/roommate/<int:profile_id>` (endpoint `profile_detail`). The JSON APIs remain
`GET /matches` and `GET /profiles/<int:profile_id>`. The old fictional
`/preview/profiles/<user_id>` placeholder path is retired, with no misleading
mapping from fictional user IDs to real profiles.

## Data and filters

`frontend.py` calls the exact registered JSON GET handlers inside the current
request, using the same `g.user`, query parameters, validation, SQL, and response
data. It converts their results into HTML through Jinja. There is no self-HTTP
request, additional query implementation, or second matching algorithm. Matching
and mutual-interest algorithms are unchanged. Separate [profile onboarding](profile-integration.md)
adds age/housing fields and completion-based login redirects using the existing auth APIs.

The form submits a normal GET, so filtering works without JavaScript. Budgets use
`min_budget` and `max_budget`, location uses `location`, and comma-separated
`interests` is redirected to repeated `interest` parameters understood by the API.
Empty interest segments are discarded. Filter values remain visible, and invalid
API filter input renders its error with HTTP 400 rather than an empty-results
message. Clear filters returns to `/find-roommates`.

Existing API semantics are preserved:

- Budget bounds are inclusive whole dollars; profiles with no budget are excluded
  when either budget filter is applied. A provided budget of zero is displayed.
- Location filtering uses the API's case-insensitive SQL LIKE behavior.
- Multiple interests match **any** listed interest.
- Ranking is descending shared-interest count, then ascending profile ID.
- The current user's own profile is excluded by the API, not a frontend algorithm.
- Default results are limited to 20; the API's `limit` query parameter still works,
  up to its existing maximum of 50. Pagination is not added.

Cards/details display actual names, preferred locations, bios, optional budgets,
and interest lists. Details now display age and housing when stored by the profile
onboarding API; older incomplete profiles never receive invented values. Profile links use
`id` (profile ID), not `user_id`. Missing fields have neutral text, and an empty
result set has a clear-filters/check-back state. Missing details return HTTP 404.
User content and filter values use Jinja's default autoescaping, with no `safe`,
`innerHTML`, or HTML interpolation through JavaScript.

Both HTML pages redirect anonymous users to login. Complete a missing/incomplete
profile through setup after login, then use Find roommates.
Details reuse the protected profile API. There is no public path exposing personal
profile data. Show Interest is now connected through the existing user-ID-based
interest API; see [interest integration](interest-integration.md). It loads the
actual relationship state and requires CSRF for sends/withdrawals.

The signed-in homepage uses up to three real API matches, excluding the current
user. Anonymous/empty homepages retain the existing floating-card design with
non-personal editorial links, never fabricated roommate profiles. The standalone
visual preview has no sample roommates or real profile access.

## Verification

From the repository root:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest src/roomie/tests/test_matches.py src/roomie/tests/test_matching_frontend.py src/roomie/tests/test_home.py tests/test_navigation.py -q
.venv/bin/python tests/browser/run_profile.py --matching-only
node --check src/static/app.js
node --check tests/browser/profile.mjs
git diff --check
```

The existing Chrome runner accepts `--matching-only` to test the real matching UI
without depending on the registration form. It uses real CSRF-protected auth and
profile APIs to prepare separate accounts in a temporary SQLite database,
including a user without a profile so profile IDs differ from user IDs. It checks
API ranking, own-profile exclusion, filters, detail links, HTML escaping, empty
states, correct interest target IDs, 404s, authentication, and layout at 1440px,
768px, and 360px. It never writes to the development database.

The previous preview-only registration template has been reconnected to its
existing API as part of profile onboarding. The full browser runner now checks
registration and profile setup/edit as well as matching. New API profile fixtures
must include name, age, preferred location, and housing_status. See the profile
guide for migration and validation details.

## Manual browser steps

1. Start the backend from `src/roomie` with
   `ROOMIE_COOKIE_SECURE=0 python -m flask --app app run --debug --port 5002`
   (the cookie override is for local HTTP only). Open `/find-roommates` logged out;
   verify login redirect. `/matches` should still return JSON 401.
2. Sign in to an existing account at `/login`, then choose **Find roommates**.
   With other saved profiles, verify actual names, locations, bios, budgets when
   provided, and interests. Your own profile must not appear. With no other
   profiles, expect the helpful empty state, never sample roommates.
3. Test budget range, location, and `cooking, hiking` together, then individually.
   Verify the URL contains repeated `interest` parameters after Apply filters.
   Clear filters and verify the API's original result order returns. Enter a
   minimum greater than the maximum to see the real API error.
4. Click **View profile**. Verify `/roommate/<profile_id>` and the correct person's
   saved content. Check the JSON `/matches` result's `id` against the link, rather
   than its `user_id`. Visit `/roommate/999999` for the missing-profile state.
   Show Interest should enable after its state loads. Clicking it should send a
   CSRF-protected POST using the target user ID, not profile ID; no POST occurs
   merely by viewing the profile. See the interest guide for two-user verification.
5. Search an unmatched location to get the empty state, then use Clear filters.
   Repeat at desktop, 768px, and 360px; inspect cards, filters, details, and account
   menu keyboard operation. Log out and revisit both HTML pages to confirm guards.
6. For budget tests, use existing profiles with budgets. My Profile now edits
   budgets at `/profile/edit`; a signed-in development account can also use the existing
   API, retaining its session and CSRF defenses:

   ```js
   const token = (await (await fetch('/auth/csrf')).json()).csrf_token;
   await fetch('/profiles/me', {
     method: 'PUT',
     headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token},
     body: JSON.stringify({budget: 600})
   });
   ```

Accounts can now be registered through `/register` and completed in `/profile/setup`.
The same real API can also create a development account from the browser console. Choose a unique
username/email and reload afterward to obtain a fresh page/CSRF token:

```js
const token = (await (await fetch('/auth/csrf')).json()).csrf_token;
const response = await fetch('/auth/register', {
  method: 'POST',
  headers: {'Content-Type': 'application/json', 'X-CSRF-Token': token},
  body: JSON.stringify({username: 'matching_review', email: 'matching_review@washburn.edu',
                        password: 'ReviewPassword123!', confirm_password: 'ReviewPassword123!'})
});
console.log(response.status, await response.json());
// On 201, open /profile/setup to save a complete real profile. Create a second account in a
// separate browser session to test results excluding the currently signed-in user.
```
