# Roomie Requirements-Based Testing and Integration Plan

## 1. Purpose

This document defines the functional testing and integration plan for the Roomie semester MVP. It translates the requirements in `docs/requirements.md` into testable checks and establishes a consistent process for reviewing features before merging into `main`.

Testing includes automated tests using pytest and the Flask test client, as well as manual browser testing.

## 2. Scope

The MVP covers requirements FR-01 through FR-11:

- User registration, login, and logout
- Profile creation and editing
- Lifestyle, interests, housing needs, and preferences
- Required-field validation
- Roommate discovery and filtering
- Safe profile display and privacy
- Sending, changing, and removing interest
- Preventing self-interest
- Protecting authenticated pages

Room listings, messaging, reporting, payments, verification, and other full-system features are outside the MVP testing scope.

## 3. Test Environment

- Python and Flask application
- SQLite database
- pytest for automated tests
- Flask test client for route and session testing
- Chrome, Firefox, Edge, and Safari when available
- macOS and Windows development environments
- Separate temporary SQLite databases for automated tests
- Seeded test accounts containing no real personal information

Automated tests must not use the local development database. Tests must be independent and reset their data before each run.

## 4. Requirements Traceability

| Requirement | Test objective | Test IDs | Expected result |
|---|---|---|---|
| FR-01 | Valid and invalid registration | TC-01 | Valid account created once; invalid or duplicate data rejected |
| FR-02 | Login, logout, and session handling | TC-02, TC-03 | Valid login creates a session; invalid login fails; logout ends the session |
| FR-03 | Profile creation and editing | TC-04, TC-05 | Profile data is saved, displayed, and updated correctly |
| FR-04 | Store lifestyle, interests, housing needs, and preferences | TC-04, TC-07 | Supported fields persist for the correct user |
| FR-05 | Required-field validation | TC-06 | Missing or invalid required fields are rejected without partial storage |
| FR-06 | Roommate filtering | TC-08 | Only matching profiles are returned |
| FR-07 | Safe profile display | TC-09 | Public profile data is visible without exposing private information |
| FR-08 | Send interest | TC-10 | Valid interest connects the correct sender and receiver |
| FR-09 | Change or remove interest | TC-11, TC-12 | Correct interest records are updated or removed |
| FR-10 | Prevent self-interest | TC-13 | Self-interest is rejected and not stored |
| FR-11 | Protect authenticated pages | TC-03, TC-14 | Unauthenticated requests are blocked or redirected |

## 5. Functional Test Cases

### TC-01: User Registration

**Related requirement:** FR-01

**Test steps:**
1. Open the registration page.
2. Enter valid registration information.
3. Submit the form.
4. Repeat with an already registered email address.
5. Repeat with invalid or missing required information.

**Expected results:**
- A valid account is created successfully.
- A success message or appropriate redirect is displayed.
- Duplicate registration is rejected.
- No duplicate or invalid account is stored.

**Testing method:** Manual browser testing and automated Flask test-client tests.

### TC-02: Login

**Related requirement:** FR-02

**Test steps:**
1. Open the login page.
2. Enter valid registered credentials.
3. Submit the form.
4. Repeat with an incorrect password.
5. Repeat with an unregistered account.

**Expected results:**
- Valid credentials create an authenticated session.
- Invalid credentials are rejected.
- Failed login attempts do not create a session.
- Error messages do not reveal whether an account exists.

**Testing method:** Manual browser testing and automated authentication tests.

### TC-03: Logout

**Related requirement:** FR-02

**Test steps:**
1. Log in with a valid account.
2. Select logout.
3. Attempt to access a protected page again.

**Expected results:**
- The authenticated session ends.
- Protected pages require authentication again.
- Previously authenticated actions cannot be performed after logout.

**Testing method:** Manual browser testing and automated session tests.

### TC-04: Profile Creation

**Related requirements:** FR-03, FR-04

**Test steps:**
1. Log in to the application.
2. Open the profile creation page.
3. Enter valid profile, lifestyle, interest, housing-need, and preference information.
4. Save the profile.
5. Reopen the profile page.

**Expected results:**
- Profile information is saved successfully.
- Saved information belongs to the correct user.
- All supported fields persist.
- The saved information displays correctly after reopening.

**Testing method:** Manual browser testing and automated Flask/database tests.

### TC-05: Profile Editing

**Related requirement:** FR-03

**Test steps:**
1. Log in and open an existing profile.
2. Change one or more editable fields.
3. Save the changes.
4. Reopen the profile.
5. Attempt to edit another user's restricted profile data.

**Expected results:**
- Updated information is saved and displayed.
- Unchanged fields remain unchanged.
- Unauthorized profile modifications are rejected.

**Testing method:** Manual browser testing and automated database/authorization tests.

### TC-06: Required-Field Validation

**Related requirement:** FR-05

**Test steps:**
1. Open registration and profile forms.
2. Submit forms with required fields missing.
3. Submit invalid field values.
4. Bypass browser-side validation and submit invalid data directly.

**Expected results:**
- Invalid submissions are rejected.
- Error messages identify fields requiring correction.
- No partial or invalid records are stored.
- Server-side validation works independently of browser validation.

**Testing method:** Manual browser testing and automated validation tests.

### TC-07: SQLite Storage and Retrieval

**Related requirements:** FR-03, FR-04, FR-05

**Test steps:**
1. Register a user and create a profile.
2. Save lifestyle, interest, housing-need, and preference data.
3. Verify records in SQLite.
4. Retrieve the profile through the application.
5. Restart the application and retrieve the data again.

**Expected results:**
- Valid records are stored correctly.
- Data is associated with the correct user.
- Saved information persists after restarting.
- Invalid or incomplete records are not stored.

**Testing method:** Automated database tests and manual application testing.

### TC-08: Roommate Filtering

**Related requirement:** FR-06

**Test steps:**
1. Seed multiple profiles with different attributes.
2. Open the roommate discovery page.
3. Apply supported filters.
4. Change or clear the filters.
5. Test a filter combination with no matching profiles.

**Expected results:**
- Results satisfy the selected filters.
- Nonmatching profiles are excluded.
- Clearing filters restores appropriate results.
- Empty results display a helpful message.

**Testing method:** Manual browser testing and automated filtering tests.

### TC-09: Protection of Private Information

**Related requirement:** FR-07

**Test steps:**
1. Create two user accounts.
2. Log in as the first user.
3. View the second user's public roommate profile.
4. Attempt to access restricted information.
5. Inspect rendered pages and application responses.

**Expected results:**
- Only intended public information is displayed.
- Password hashes, email addresses where private, and login data are not exposed.
- Unauthorized access to restricted information is denied.
- Private data is not included in unintended application responses.

**Testing method:** Manual browser testing and automated privacy/authorization tests.

### TC-10: Sending Interest

**Related requirement:** FR-08

**Test steps:**
1. Log in as a registered user.
2. Open another eligible user's profile.
3. Select the interest action.
4. Check the resulting state and database record.
5. Repeat the action to check duplicate handling.

**Expected results:**
- Interest is recorded for the correct sender and receiver.
- The interface displays confirmation or an updated state.
- Interest persists after reopening the page.
- Duplicate interest is prevented or handled according to defined rules.

**Testing method:** Manual browser testing and automated Flask/database tests.

### TC-11: Changing Interest

**Related requirement:** FR-09

**Test steps:**
1. Log in with an existing interest record.
2. Change the interest status using the available interface.
3. Reopen the relevant page.
4. Attempt an invalid status change.

**Expected results:**
- The correct interest record is updated.
- The updated status is stored and displayed.
- Invalid status changes are rejected.
- Other users' interest records remain unchanged.

**Testing method:** Manual browser testing and automated state-update tests.

### TC-12: Removing Interest

**Related requirement:** FR-09

**Test steps:**
1. Log in with an existing interest record.
2. Remove or withdraw the interest.
3. Reopen the page.
4. Attempt to remove another user's interest record.

**Expected results:**
- Interest is removed or marked inactive according to the design.
- The interface reflects the change.
- Removed interest is no longer treated as active.
- Unauthorized deletion or modification is rejected.

**Testing method:** Manual browser testing and automated Flask/database tests.

### TC-13: Preventing Self-Matching and Self-Interest

**Related requirements:** FR-06, FR-10

**Test steps:**
1. Log in and open roommate discovery.
2. Check whether the current user's profile appears as an eligible match.
3. Attempt to send interest to the current user's own account.
4. Repeat using a direct request where applicable.

**Expected results:**
- The current user is excluded from eligible roommate matches.
- Self-interest requests are rejected.
- No self-interest record is stored.
- Server-side validation enforces the restriction.

**Testing method:** Manual browser testing and automated filtering/database tests.

### TC-14: Blocking Unauthenticated Access

**Related requirement:** FR-11

**Test steps:**
1. Log out or open a fresh browser session.
2. Enter the direct URL of protected pages.
3. Attempt profile editing, matching, and interest actions.
4. Repeat after logging in and logging out.

**Expected results:**
- Protected content cannot be accessed without authentication.
- Unauthorized requests redirect to login or return the intended unauthorized response.
- Protected actions cannot be performed through direct requests.
- Logging out prevents further access using the previous session.

**Testing method:** Manual browser testing and automated Flask test-client tests.

## 6. Integration Testing Checklist

Integration testing verifies that the interface, Flask backend, validation logic, SQLite database, and rendered results work together.

### 6.1 HTML Forms to Flask

- [ ] Registration form submits to the correct Flask route.
- [ ] Login form sends credentials to the correct route.
- [ ] Profile creation and editing forms submit expected fields.
- [ ] Roommate filters reach the correct backend route.
- [ ] Interest actions send the correct sender and receiver information.
- [ ] Forms use the expected HTTP methods and field names.

### 6.2 Flask Validation

- [ ] Required fields are validated on the server.
- [ ] Invalid email addresses and other invalid values are rejected.
- [ ] Duplicate registrations are handled correctly.
- [ ] Invalid profile updates are rejected.
- [ ] Unauthorized requests are blocked.
- [ ] Self-interest attempts are rejected.
- [ ] Validation failures do not save invalid records.

### 6.3 Flask to SQLite

- [ ] Flask connects to the correct SQLite database.
- [ ] Registration creates the expected user record.
- [ ] Login retrieves user information and securely verifies credentials.
- [ ] Profile creation and editing update the correct records.
- [ ] Interest actions affect the correct sender-receiver relationship.
- [ ] Failed writes are rolled back.
- [ ] Database errors do not expose sensitive information.
- [ ] Connections and transactions are handled appropriately.

### 6.4 SQLite Storage and Retrieval

- [ ] Registered users can be retrieved.
- [ ] Saved profiles contain correct information.
- [ ] Edited profiles return updated values.
- [ ] Preference and lifestyle fields persist.
- [ ] Interest records can be created, changed, and removed.
- [ ] Data persists after restarting the application.
- [ ] Duplicate and invalid records are prevented where required.

### 6.5 Interface Results

- [ ] Successful registration displays the expected response.
- [ ] Login displays the authenticated interface.
- [ ] Profile pages display saved information.
- [ ] Profile edits appear after saving.
- [ ] Roommate results match selected filters.
- [ ] Interest status is displayed correctly.
- [ ] Empty search results are handled clearly.
- [ ] Updated information is displayed without stale values.

### 6.6 Error Handling

- [ ] Missing fields produce clear messages.
- [ ] Invalid credentials produce appropriate errors.
- [ ] Duplicate registration produces a useful error.
- [ ] Invalid profile updates are explained.
- [ ] Database errors do not expose secrets.
- [ ] Unauthorized access is handled safely.
- [ ] Error messages do not reveal unnecessary technical details.

### 6.7 macOS and Windows Compatibility

- [ ] Application and tests run on a supported macOS environment.
- [ ] Application and tests run on a supported Windows environment.
- [ ] Documented Python and dependency versions work on both.
- [ ] SQLite creation and access work on both.
- [ ] File paths and database configurations are compatible.
- [ ] Main MVP workflows operate in browsers on both systems.
- [ ] Redirects, forms, and error messages behave consistently.
- [ ] Platform-specific failures and resolutions are documented.

## 7. Nonfunctional Testing

### 7.1 Performance

- Measure normal page requests during team testing; at least 95% should complete within three seconds.
- Seed 500 profiles and verify a supported match search completes within two seconds.
- Confirm every submitted form displays success or error feedback.

### 7.2 Reliability

- Invalid input must not create partial account or profile records.
- Failed database writes must be rolled back.
- Critical automated tests must pass before the MVP demonstration.
- Defects must be recorded in Trello with reproduction steps and assigned owners.

### 7.3 Security and Privacy

- Passwords must be hashed and never displayed or logged in plaintext.
- Protected routes must reject unauthenticated requests.
- SQL operations must use parameterized queries.
- Inputs must be checked for length limits, unexpected values, and unsafe characters.
- Secret keys, virtual environments, and SQLite database files must not be committed.
- Login errors must not reveal whether an account exists.

### 7.4 Interface and Compatibility

- Test layouts at approximately 360px and 1280px viewport widths.
- Required fields must have visible labels.
- Registration, profile, preference, and matching workflows must support keyboard navigation.
- Error messages must identify the field or action requiring correction.
- Test current team versions of Chrome, Firefox, Edge, and Safari when available.

## 8. Integration and Pull Request Process

1. Pull the latest `main` before beginning work.
2. Implement or test one focused feature on a separate branch.
3. Run the related automated tests locally.
4. Run critical tests using a temporary SQLite database.
5. Manually test the affected workflow.
6. Open a pull request describing the related requirement IDs.
7. Review code changes, test results, and database effects.
8. Fix failures on the feature branch and rerun tests.
9. Merge only when the reviewer confirms critical tests pass and no secrets or local database files are exposed.

## 9. Test Execution and Reporting

Each test must be recorded as **Pass**, **Fail**, or **Not Run**.

| Test ID | Requirement(s) | Result | Notes |
|---|---|---|---|
| TC-01 | FR-01 | Not Run | |
| TC-02 | FR-02 | Not Run | |
| TC-03 | FR-02 | Not Run | |
| TC-04 | FR-03, FR-04 | Not Run | |
| TC-05 | FR-03 | Not Run | |
| TC-06 | FR-05 | Not Run | |
| TC-07 | FR-03, FR-04, FR-05 | Not Run | |
| TC-08 | FR-06 | Not Run | |
| TC-09 | FR-07 | Not Run | |
| TC-10 | FR-08 | Not Run | |
| TC-11 | FR-09 | Not Run | |
| TC-12 | FR-09 | Not Run | |
| TC-13 | FR-06, FR-10 | Not Run | |
| TC-14 | FR-11 | Not Run | |

## 10. Defect Reporting

Each defect should include:

- Short descriptive title
- Related requirement ID
- Test environment and browser
- Steps to reproduce
- Expected result
- Actual result
- Severity: critical, major, normal, or minor
- Screenshot or error output when useful
- Assigned owner
- Retest status

A critical defect blocks authentication, corrupts or exposes data, bypasses authorization, or prevents the main MVP workflow. Critical defects must be fixed before the MVP demonstration.

## 11. Entry, Exit, and Completion Criteria

Testing can begin when a requirement has an implemented route or interface and a repeatable setup process.

A feature is ready for review when:

- Its requirement-based tests pass.
- No critical or major defect remains open.
- Invalid input is handled without partial storage.
- Authentication and privacy checks pass where applicable.
- Manual browser behavior matches the requirement.
- Setup and test instructions are updated.
- The pull request identifies the tested requirement IDs.

The MVP testing phase is complete when:

- Every MVP requirement is mapped to at least one test.
- All applicable functional tests have been executed.
- Failed tests and unresolved defects are documented.
- Integration checklist items are verified or recorded as not run.
- Supported macOS and Windows environments have been tested.
- Results have been reviewed before the MVP demonstration.

## 12. Current Dependencies and Responsibilities

Test cases and traceability can be prepared before backend implementation is complete.

Final automated integration tests depend on stable Flask routes, SQLite schema, validation rules, and service behavior.

Rajju, responsible for testing and QA, should update test names, commands, and implementation-specific details to match the completed application rather than assuming draft route or function names.

Backend, frontend, and database contributors should coordinate changes affecting form fields, routes, session handling, and stored data.

**Important:** Requirement IDs in this document follow the FR-01 through FR-11 mapping supplied in the requirements-based plan. Verify them against the latest `docs/requirements.md` before final approval.
## 13. Initial Testing Results – November 16, 2026

### Test Environment
- ChromeOS Linux
- Python 3.13.5
- Flask 3.1.3
- Pytest 9.2.0

### Initial Test Results
Command: `python -m pytest -v`

- Tests collected: 4
- Passed: 4
- Failed: 0

### Tests Verified
- Public navigation and registration.
- Unauthenticated redirects from profile and preferences.
- Rejection of an unverified user.
- Authenticated-user template behavior using test fixtures.

### Current Limitations
The current main branch contains the Flask preview application and frontend templates. Backend authentication, SQLite integration, profile management, roommate matching, and interest functionality were not found in the inspected source files.

The four passing tests verify preview behavior only, not the complete MVP.

### Pending Testing Work
- Registration, login, and logout.
- Profile creation and editing.
- Preferences and SQLite persistence.
- Roommate matching and filtering.
- Profile privacy and ownership.
- Interest creation, changes, and removal.
- Self-interest prevention.
- Protected-page authorization.
## 14. Backend Testing Results – November 25, 2026


### Full Test Results

**Command used:**
```bash
PYTHONPATH=src/roomie python -m pytest -v
```

**Results:**
- 131 tests collected
- 130 tests passed
- 1 test failed

The tests covered authentication, database operations, user profiles, preferences, roommate matching, interest functionality, and frontend navigation.

### Failed Test

The failing test was `test_register_works_with_html_form`.

The test sent regular HTML form data, but the backend registration route currently reads JSON data. Because the backend did not receive JSON, it returned None, which caused an AttributeError.

This issue needs clarification. The team needs to decide whether the registration route should accept regular HTML form submissions or whether the frontend should send JSON instead.

### Conclusion

Most automated tests passed successfully. The remaining issue concerns the expected format of registration data. The frontend forms and backend routes also need to be fully connected before integration can be considered complete.
