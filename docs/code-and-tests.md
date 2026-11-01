# Roomie Code and Test Reference

This document explains what each function in the Roomie back end does and what each automated test checks. The code lives in `src/roomie/app/` and the tests live in `src/roomie/tests/`.

## Current test status

**85 of 87 tests pass.** This was last checked on 2026-11-01.

| Test file | Tests | Result |
|---|---:|---|
| `test_db.py` | 11 | All pass |
| `test_interest.py` | 17 | All pass |
| `test_matches.py` | 21 | All pass |
| `test_profiles.py` | 22 | All pass |
| `tests_auth.py` | 16 | 2 fail (issues 1 and 2 below) |

To run all the tests, start in `src/roomie` and run both commands. The first command skips `tests_auth.py` because its name doesn't match pytest's `test_*.py` pattern, and adding the file to the same command doesn't bring it back.

```powershell
.\.venv\Scripts\python.exe -m pytest tests
.\.venv\Scripts\python.exe -m pytest tests/tests_auth.py
```

## Known issues

| # | Issue | Effect |
|---:|---|---|
| 1 | `test_register_success` expects the ID `"user-001"` | The test is out of date. IDs became integers in the move to SQLite, so the API correctly returns `1`. |
| 2 | `register` and `login` assume the request body is a JSON object | Form data, a missing body or a JSON array returns a 500 error. `test_register_works_with_html_form` fails because of this. |
| 3 | `_clean` also assumes a JSON object | Sending a JSON array to `POST /profiles` returns a 500 error. `PUT /profiles/me` uses the same check. |
| 4 | `_whole_number` accepts characters such as `²`, which `isdigit()` counts as digits but `int()` rejects | `GET /matches?max_budget=²` returns a 500 error instead of a 400. |
| 5 | `limit or DEFAULT_LIMIT` treats 0 as "not set" | `GET /matches?limit=0` uses the default limit of 20 instead of returning no results. |
| 6 | Unused leftovers from the JSON storage version | `USERS_FILE` and `next_user_id` in `auth.py` and `import uuid` in `profile.py` can be removed. |
| 7 | `test_init_db_command` only checks the printed message | The test would still pass if `flask init-db` stopped creating tables. |

## How a request works

1. `load_logged_in_user` runs first and puts the current user, or `None`, in `g.user`.
2. Flask finds the route. Routes that use `@login_required` return a 401 error if nobody is logged in.
3. The route opens the database with `get_db` and returns JSON. Errors have the form `{"error": "message"}`.
4. `close_db` closes the database connection when the request ends.

The logged-in user's ID always comes from the session and never from the request body, so nobody can act as another user by sending a different ID.

## API endpoints

| Method and path | Login needed | Function | Purpose |
|---|---:|---|---|
| `GET /health` | No | `health` | Check that the app is running |
| `POST /auth/register` | No | `register` | Create an account and log in |
| `POST /auth/login` | No | `login` | Log in |
| `POST /auth/logout` | No | `logout` | Log out |
| `GET /auth/me` | Yes | `me` | Get the logged-in user |
| `POST /profiles` | Yes | `create_profile` | Create your profile |
| `GET /profiles` | Yes | `list_profiles` | List all profiles |
| `GET /profiles/me` | Yes | `get_my_profile` | Get your profile |
| `PUT /profiles/me` | Yes | `update_my_profile` | Edit your profile |
| `GET /profiles/<id>` | Yes | `get_profile` | Get one profile |
| `GET /matches` | Yes | `find_matches` | Search and rank possible roommates |
| `POST /interest/<user_id>` | Yes | `show_interest` | Show interest in a user |
| `DELETE /interest/<user_id>` | Yes | `withdraw_interest` | Take back your interest |
| `GET /interest/sent` | Yes | `sent` | List people you showed interest in |
| `GET /interest/received` | Yes | `received` | List people interested in you |
| `GET /interest/mutual` | Yes | `mutual` | List people where the interest goes both ways |

## Database tables

These are defined in `app/schema.sql`.

| Table | Stores | Rules enforced by the database |
|---|---|---|
| `users` | Accounts | Username and email are unique, ignoring case |
| `profiles` | One roommate profile per user | One profile per user; budget can't be negative |
| `profile_interests` | Each interest on a profile, one per row | A profile can't list the same interest twice |
| `connection_requests` | One row for each "A showed interest in B" | No repeats; no interest in yourself |

Deleting a user also deletes their profile, interests and connection requests.

## Application functions

### `app/__init__.py`: app setup

| Function | What it does |
|---|---|
| `create_app(test_config=None)` | Builds the Flask app, loads its settings, connects the database functions and registers the four blueprints. Tests pass in their own settings. |
| `health()` | Returns `{"status": "ok"}` so you can check that the app is running. |

### `app/db.py`: database connection

| Function | What it does |
|---|---|
| `get_db()` | Returns the database connection for the current request, opening it on first use. Rows can be read by column name, and foreign key rules are turned on. |
| `close_db(e=None)` | Closes the connection when the request ends. |
| `init_db()` | Runs `schema.sql`. **This deletes all existing data** and recreates the tables. |
| `init_db_command()` | The `flask init-db` command, which runs `init_db` and prints a success message. |
| `init_app(app)` | Registers `close_db` and the `init-db` command on the app. |

### `app/auth.py`: accounts and login

| Function | What it does |
|---|---|
| `get_input()` | Reads the JSON request body, or returns `None` if it can't. |
| `next_user_id(users)` | Unused leftover from JSON storage (issue 6). |
| `public(user)` | Keeps only the fields that are safe to return: ID, username, email and creation date. This leaves out the password hash. |
| `_error(message, status)` | Builds a JSON error response. |
| `load_logged_in_user()` | Runs before every request and puts the current user, or `None`, in `g.user`. |
| `login_required(view)` | Decorator that returns a 401 error unless someone is logged in. |
| `register()` | Validates the username (3-30 letters, numbers or underscores), email and password (at least 8 characters). It then rejects duplicates with a 409 error, saves the account with a hashed password and logs the user in. |
| `login()` | Checks the email and password and starts a new session. A wrong password and an unknown email get the same message, so nobody can find out which emails have accounts. |
| `logout()` | Clears the session. |
| `me()` | Returns the logged-in user so the front end can tell who is logged in. |

### `app/profile.py`: roommate profiles

| Function | What it does |
|---|---|
| `_error(message, status)` | Builds a JSON error response. |
| `_clean(data, require_name)` | Validates profile input and returns `(cleaned_fields, None)` or `(None, error_message)`. It reads only name, bio, budget, preferred location and interests, so extra fields like `user_id` are ignored. Interests are lowercased and duplicates are removed. |
| `_to_dict(row)` | Converts a profile row to JSON, including its interests. |
| `_save_interests(db, profile_id, interests)` | Replaces all of a profile's interests with the new list. |
| `_my_profile()` | Gets the logged-in user's profile, or `None`. |
| `create_profile()` | Creates the user's profile. Returns a 400 error for invalid input and a 409 error if they already have one. |
| `list_profiles()` | Returns all profiles, oldest first. |
| `get_my_profile()` | Returns the user's own profile, or a 404 error. |
| `update_my_profile()` | Changes only the fields that were sent and updates `updated_at`. Sending interests replaces the whole list. |
| `get_profile(profile_id)` | Returns one profile by ID, or a 404 error. |

### `app/matches.py`: finding roommates

| Function | What it does |
|---|---|
| `_error(message, status)` | Builds a JSON error response. |
| `_whole_number(name)` | Reads an optional whole-number query parameter and returns `(value, error)`. |
| `_interests_for(profile_id)` | Returns the list of interests on a profile. |
| `find_matches()` | Searches other users' profiles and ranks them by how many interests they share with you. Ties go to the older profile. |

`find_matches` accepts these optional filters:

| Parameter | Effect |
|---|---|
| `max_budget`, `min_budget` | Limit the budget range. Profiles with no budget are left out. |
| `location` | Matches part of the location, ignoring case. |
| `interest` | Can be repeated. A profile needs any one of the listed interests. |
| `limit` | Sets the number of results. The default is 20 and the maximum is 50. |

### `app/interests.py`: showing interest

A "mutual match" means two users have each shown interest in the other.

| Function | What it does |
|---|---|
| `_error(message, status)` | Builds a JSON error response. |
| `_person(row)` | Builds a list entry with `user_id`, `username`, `name`, `profile_id` and `since`. It contains no email or password. |
| `_is_mutual(db, me, other)` | Returns whether the other user has already shown interest in you. |
| `show_interest(user_id)` | Saves your interest and reports whether it is now mutual. Returns a 400 error for yourself, a 404 error for an unknown user and a 409 error for a repeat. |
| `withdraw_interest(user_id)` | Deletes your own interest, or returns a 404 error if there is none. |
| `sent()` | Lists the people you showed interest in, newest first. |
| `received()` | Lists the people who showed interest in you, newest first. |
| `mutual()` | Lists the people where the interest goes both ways, sorted by when the match happened. |

## Tests

### `tests/conftest.py`: shared fixtures

| Fixture | What it provides |
|---|---|
| `app` | A fresh app with its own empty temporary database, so tests can't affect each other |
| `client` | A fake browser for sending requests; it keeps login cookies between requests |
| `runner` | A way to run command-line commands such as `init-db` |
| `db` | A direct database connection for tests that skip the API |

### `tests/test_db.py`: database setup and rules

| Test | What it checks |
|---|---|
| `test_health` | `/health` returns 200 and `{"status": "ok"}` |
| `test_tables_exist` | All four tables are created |
| `test_same_connection_within_request` | Calling `get_db` twice returns the same connection |
| `test_connection_closed_after_request` | The connection can't be used after the request ends |
| `test_init_db_command` | `init-db` prints its success message, but not that it created any tables (issue 7) |
| `test_data_survives_restart` | Saved data is still there after creating a new app on the same file |
| `test_foreign_keys_enforced` | A profile can't point to a user who doesn't exist |
| `test_no_negative_budget` | The database rejects a negative budget |
| `test_no_connection_request_to_self` | The database rejects interest in yourself |
| `test_no_duplicate_connection_request` | The database rejects the same interest twice |
| `test_deleting_user_removes_their_data` | Deleting a user also removes their profile, interests and requests |

Helper: `_user(db, name)` adds a user directly to the database.

### `tests/tests_auth.py`: accounts and login

| Test | What it checks |
|---|---|
| `test_register_success` | **Fails (issue 1).** Registering returns 201, saves the email and doesn't store the plain password |
| `test_register_does_not_return_password_hash` | The response never includes the password hash |
| `test_register_logs_user_in` | A new user is logged in straight away |
| `test_register_duplicate_email` | A repeated email returns 409, ignoring case, and adds no user |
| `test_register_duplicate_username` | A repeated username returns 409, ignoring case |
| `test_register_short_password` | A short password returns 400 |
| `test_register_bad_email` | An invalid email returns 400 |
| `test_register_bad_username` | A username with a space returns 400 |
| `test_register_missing_fields` | An empty body returns 400 |
| `test_register_works_with_html_form` | **Fails (issue 2).** Registering with form data instead of JSON returns 201 |
| `test_login_success` | Logging in works and the session shows the right user |
| `test_login_email_is_case_insensitive` | Email capitalization doesn't matter at login |
| `test_login_wrong_password` | A wrong password returns 401 and doesn't log the user in |
| `test_login_unknown_email_same_message` | A wrong password and an unknown email get the same response |
| `test_logout` | After logging out, `/auth/me` returns 401 |
| `test_me_requires_login` | `/auth/me` returns a 401 JSON error when logged out |

Helpers: `register` and `login` send those requests, and `user_count` counts the saved users.

### `tests/test_profiles.py`: roommate profiles

| Test | What it checks |
|---|---|
| `test_create_profile` | Creating a profile returns 201 with all the fields saved |
| `test_create_profile_requires_login` | Creating while logged out returns 401 and saves nothing |
| `test_user_id_comes_from_login_not_request` | A `user_id` in the request is ignored |
| `test_only_one_profile_per_user` | A second profile returns 409 and isn't saved |
| `test_create_profile_requires_name` | A missing or blank name returns 400 |
| `test_create_profile_rejects_negative_budget` | A negative budget returns 400 |
| `test_create_profile_rejects_non_number_budget` | The budgets `"700"`, `70.5` and `True` each return 400 (3 test cases) |
| `test_create_profile_rejects_bad_interests` | Interests that aren't a list, or more than 10, return 400 |
| `test_interests_are_cleaned` | Interests are trimmed and lowercased, and duplicates are removed |
| `test_get_all_profiles` | All users' profiles are listed in order |
| `test_get_single_profile` | One profile is returned with its interests |
| `test_get_missing_profile` | An unknown profile returns 404 with the expected message |
| `test_viewing_requires_login` | Viewing profiles while logged out returns 401 |
| `test_get_my_profile` | `/profiles/me` returns 404 before a profile exists and the profile afterwards |
| `test_update_my_profile` | Sent fields change and the others stay the same |
| `test_update_replaces_interests` | New interests replace the old list |
| `test_update_cannot_change_owner_or_id` | `user_id` and `id` can't be changed |
| `test_update_validates` | Invalid updates return 400 |
| `test_update_without_profile` | Updating before creating a profile returns 404 |
| `test_cannot_edit_someone_elses_profile` | A second user's edit doesn't change the first user's profile |

Helpers: `register`, `create` and `profile_count` handle common steps, and the `logged_in` fixture provides a client logged in as `arpan`.

### `tests/test_matches.py`: finding roommates

The `town` fixture creates four users, then searches as `arpan`, whose interests are gaming and cooking:

| User | Budget | Location | Interests | Shared with `arpan` |
|---|---:|---|---|---:|
| `stuti` | 600 | Topeka, KS | gaming, cooking | 2 |
| `swikar` | 700 | Topeka, KS | gaming | 1 |
| `rajju` | 900 | Lawrence, KS | hiking | 0 |

| Test | What it checks |
|---|---|
| `test_requires_login` | Searching while logged out returns 401 |
| `test_never_shows_my_own_profile` | Your own profile isn't in the results |
| `test_ranked_by_shared_interests` | Results are ordered by the number of shared interests |
| `test_shows_which_interests_are_shared` | Results include the shared interests and their count |
| `test_works_without_my_own_profile` | A user with no profile can search, with 0 shared interests |
| `test_no_other_users` | With nobody else on the site, the result is an empty list |
| `test_filter_max_budget` | `max_budget` leaves out higher budgets |
| `test_filter_min_budget` | `min_budget` leaves out lower budgets |
| `test_filter_budget_range` | Both budget filters work together |
| `test_budget_filter_skips_profiles_without_budget` | Budget filters leave out profiles with no budget |
| `test_filter_location_is_case_insensitive_and_partial` | Part of a location matches, ignoring case |
| `test_filter_one_interest` | One `interest` filter works |
| `test_filter_several_interests_means_any` | With several interests, a profile needs any one of them |
| `test_filters_combine` | Different filters work together |
| `test_limit` | `limit` caps the number of results |
| `test_bad_filters_return_400` | Non-numeric, negative or decimal values, and a minimum above the maximum, return 400 (5 test cases) |
| `test_sql_injection_in_location_is_just_text` | SQL typed into `location` is treated as plain text and returns no results |

Helpers: `register`, `make_user` and `names` handle common steps.

### `tests/test_interest.py`: showing interest

The `people` fixture creates `arpan`, `stuti` and `rajju` with profiles, then logs in as `arpan`.

| Test | What it checks |
|---|---|
| `test_requires_login` | All five interest endpoints return 401 when logged out |
| `test_show_interest` | Showing interest returns 201 with `mutual: false` |
| `test_cannot_show_interest_in_self` | Showing interest in yourself returns 400 |
| `test_unknown_user` | An unknown user returns 404 with "User not found" |
| `test_duplicate_interest` | Showing interest twice returns 409 |
| `test_second_person_gets_mutual_true` | The person who completes a match gets `mutual: true` |
| `test_sent_list` | The sent list contains the people you showed interest in |
| `test_received_list` | The received list contains the people interested in you, with names |
| `test_received_does_not_include_sent` | Interest you sent isn't in your received list |
| `test_list_shows_safe_fields_only` | List entries contain only the five safe fields |
| `test_person_without_profile_still_listed` | Someone with no profile is listed with `name` and `profile_id` as `None` |
| `test_mutual_needs_both_sides` | One-way interest isn't a match |
| `test_mutual_match` | Both people see each other, and one-way interests stay out |
| `test_withdraw` | Withdrawing removes the interest, and you can send it again afterwards |
| `test_withdraw_nothing` | Withdrawing interest you never showed returns 404 with the expected message |
| `test_withdraw_breaks_mutual` | Withdrawing ends the match |
| `test_cannot_withdraw_someone_elses_interest` | You can't delete another user's interest |

Helpers: `login_as` switches between users, and `user_ids` gets the IDs from a list response.
