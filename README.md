# Roomie MVP Testing Plan

## 1. Purpose

This document describes the functional tests and integration checks for the Roomie MVP application. The goal is to verify that users can register, log in, manage profiles, find potential roommates, express interest, and access only the information and pages they are authorized to use.

Testing includes manual browser testing and automated tests where supported by the application.

## 2. Functional Test Cases

### TC-01: User Registration

**Test ID:** TC-01  
**Related requirement:** FR-01 — User registration  
**Test action:**
1. Open the registration page.
2. Enter valid registration information.
3. Submit the form.
4. Repeat with an email address that is already registered.

**Expected result:**
- A valid new user account is created.
- The user receives an appropriate success message or is redirected to the expected page.
- Duplicate registration is rejected with a clear error message.
- No duplicate account is created.

**Testing method:** Manual browser testing; automated Flask test-client tests.

### TC-02: Login

**Test ID:** TC-02  
**Related requirement:** FR-02 — User login  
**Test action:**
1. Open the login page.
2. Enter valid credentials for a registered user.
3. Submit the form.
4. Repeat with an incorrect password or an unregistered email address.

**Expected result:**
- Valid credentials allow the user to log in.
- Invalid credentials are rejected.
- An appropriate error message is displayed.
- Failed login attempts do not create an authenticated session.

**Testing method:** Manual browser testing; automated Flask test-client tests.

### TC-03: Logout

**Test ID:** TC-03  
**Related requirement:** FR-03 — User logout  
**Test action:**
1. Log in with a valid account.
2. Select the logout option.
3. Attempt to access a protected page again.

**Expected result:**
- The user is logged out.
- The authenticated session is cleared or invalidated.
- Protected pages require the user to log in again.

**Testing method:** Manual browser testing; automated session tests.

### TC-04: Profile Creation

**Test ID:** TC-04  
**Related requirement:** FR-04 — Profile creation  
**Test action:**
1. Log in to the application.
2. Open the profile creation page.
3. Enter valid profile information.
4. Save the profile.
5. Reopen the profile page.

**Expected result:**
- The profile is saved successfully.
- The saved information is associated with the correct user.
- The profile displays the saved information after reopening the page.

**Testing method:** Manual browser testing; automated Flask and database tests.

### TC-05: Profile Editing

**Test ID:** TC-05  
**Related requirement:** FR-05 — Profile editing  
**Test action:**
1. Log in and open an existing profile.
2. Change one or more editable fields.
3. Save the changes.
4. Reopen the profile.

**Expected result:**
- The updated information is saved and displayed.
- Unchanged information remains unchanged.
- A user cannot modify another user's private profile information without authorization.

**Testing method:** Manual browser testing; automated Flask and database tests.

### TC-06: Required-Field Validation

**Test ID:** TC-06  
**Related requirement:** FR-06 — Required-field validation  
**Test action:**
1. Open the registration or profile form.
2. Submit the form with one or more required fields empty.
3. Submit the form with invalid field values where applicable.

**Expected result:**
- The application rejects missing or invalid required fields.
- Clear error messages identify the fields that need correction.
- Invalid information is not saved to the database.
- Server-side validation works even if browser-side validation is bypassed.

**Testing method:** Manual browser testing; automated validation tests.

### TC-07: SQLite Storage and Retrieval

**Test ID:** TC-07  
**Related requirement:** FR-07 — Persistent data storage and retrieval  
**Test action:**
1. Register a user and save a profile.
2. Verify that the records are stored in SQLite.
3. Retrieve the profile through the application.
4. Restart the application and retrieve the saved information again.

**Expected result:**
- Valid user and profile information is stored in SQLite.
- The correct records are retrieved and associated with the correct user.
- Saved data persists after an application restart.
- Invalid or incomplete data is not stored.

**Testing method:** Automated database tests; manual application testing.

### TC-08: Roommate Filtering

**Test ID:** TC-08  
**Related requirement:** FR-08 — Roommate filtering  
**Test action:**
1. Create or prepare multiple profiles with different filter attributes.
2. Open the roommate search page.
3. Apply available filters, such as location or preferences.
4. Repeat with different filter values and with no matching results.

**Expected result:**
- The displayed profiles match the selected filters.
- Profiles that do not meet the selected criteria are excluded.
- Clearing filters restores the appropriate unfiltered results.
- An empty result set is handled with a helpful message.

**Testing method:** Manual browser testing; automated filtering tests.

### TC-09: Protection of Private Information

**Test ID:** TC-09  
**Related requirement:** FR-09 — Privacy and access control  
**Test action:**
1. Create two different user accounts.
2. Log in as the first user and inspect the profile and roommate results.
3. Attempt to access information that should be private or belongs exclusively to the second user.
4. Inspect application responses and rendered pages for unintended disclosure.

**Expected result:**
- Only information intended to be visible to other users is displayed.
- Private information is not exposed through pages or application responses.
- Users cannot access another user's restricted information without authorization.
- Unauthorized access attempts are denied.

**Testing method:** Manual browser testing; automated authorization and response tests.

### TC-10: Sending Interest

**Test ID:** TC-10  
**Related requirement:** FR-10 — Sending interest  
**Test action:**
1. Log in as one user.
2. Open another eligible user's roommate profile.
3. Select the option to express interest.
4. Check the resulting application state and database record.

**Expected result:**
- Interest is recorded for the correct sender and recipient.
- The application displays an appropriate confirmation or updated state.
- The interest record persists when the relevant page is reopened.
- Duplicate interest is prevented or handled according to the application's defined rules.

**Testing method:** Manual browser testing; automated Flask and database tests.

### TC-11: Changing Interest

**Test ID:** TC-11  
**Related requirement:** FR-10 — Changing interest  
**Test action:**
1. Log in as a user who has already expressed interest in another user.
2. Change the interest status using the available interface.
3. Reopen the relevant page and verify the updated state.

**Expected result:**
- The interest status changes to the requested valid state.
- The new state is saved and displayed consistently.
- The update applies to the correct interest record.
- Invalid status changes are rejected.

**Testing method:** Manual browser testing; automated state-update tests.

### TC-12: Removing Interest

**Test ID:** TC-12  
**Related requirement:** FR-10 — Removing interest  
**Test action:**
1. Log in as a user who has an existing interest record.
2. Select the option to remove or withdraw interest.
3. Reopen the page and check the interest state.

**Expected result:**
- The interest is removed or marked inactive according to the application's design.
- The interface reflects the updated state.
- The removed interest is no longer treated as active.
- A user cannot remove another user's interest without authorization.

**Testing method:** Manual browser testing; automated Flask and database tests.

### TC-13: Preventing Self-Matching and Self-Interest

**Test ID:** TC-13  
**Related requirement:** FR-11 — Preventing self-matching and self-interest  
**Test action:**
1. Log in as a user and open the roommate search page.
2. Check whether the user's own profile appears as a potential roommate.
3. Attempt to send interest to the same user's account, including through a direct request if applicable.

**Expected result:**
- The current user is excluded from eligible roommate matches.
- The application rejects attempts to express interest in oneself.
- No self-interest record is created in SQLite.
- The restriction is enforced on the server, not only in the interface.

**Testing method:** Manual browser testing; automated filtering, validation, and database tests.

### TC-14: Blocking Unauthenticated Access to Protected Pages

**Test ID:** TC-14  
**Related requirement:** Authentication and authorization requirements for protected pages  
**Test action:**
1. Log out or open a fresh browser session.
2. Enter the direct URL of each protected page.
3. Attempt to access profile editing, roommate actions, and other protected features without logging in.
4. Repeat after logging in and then logging out.

**Expected result:**
- Unauthenticated users cannot view protected content or perform protected actions.
- The application redirects the user to the login page or returns an appropriate unauthorized response.
- Protected actions cannot be performed through direct requests without authentication.
- Logging out prevents continued access to protected pages through the previous session.

**Testing method:** Manual browser testing; automated Flask test-client tests.

## 3. Integration Testing Checklist

Integration testing verifies that the interface, Flask backend, validation logic, SQLite database, and result pages work together correctly.

### 3.1 HTML Form to Flask

- [ ] Registration form submits data to the correct Flask route.
- [ ] Login form sends credentials to the correct Flask route.
- [ ] Profile creation and editing forms submit the expected fields.
- [ ] Roommate filter selections reach the correct backend route.
- [ ] Interest actions send the correct user and target information.
- [ ] Form submissions use the expected HTTP method and field names.

### 3.2 Flask Validation

- [ ] Flask checks required fields on the server.
- [ ] Invalid email addresses and other invalid values are rejected where applicable.
- [ ] Duplicate registrations are handled correctly.
- [ ] Invalid profile updates are rejected.
- [ ] Unauthorized requests are blocked.
- [ ] Self-interest and self-matching attempts are rejected.
- [ ] Validation failures do not save invalid records to SQLite.

### 3.3 Flask to SQLite

- [ ] Flask connects to the correct SQLite database.
- [ ] Registration creates the expected user record.
- [ ] Login retrieves the correct user record and verifies credentials securely.
- [ ] Profile creation and editing update the correct records.
- [ ] Interest actions affect the correct sender-recipient relationship.
- [ ] Database operations handle errors without exposing sensitive information.
- [ ] Database connections and transactions are handled appropriately.

### 3.4 SQLite Storage and Retrieval

- [ ] Newly registered users can be retrieved from the database.
- [ ] Saved profiles can be retrieved with the correct information.
- [ ] Edited profiles return the latest saved values.
- [ ] Interest records can be created, updated, and removed as designed.
- [ ] Data remains available after restarting the application.
- [ ] Duplicate or invalid records are prevented where required.

### 3.5 Results Displayed in the Interface

- [ ] Successful registration displays the expected confirmation or next page.
- [ ] Login displays the expected authenticated page.
- [ ] Profile pages display saved information.
- [ ] Edited profile information appears after saving.
- [ ] Roommate results match the selected filters.
- [ ] Interest status is reflected correctly in the interface.
- [ ] Empty search results are handled clearly.
- [ ] Updated data is displayed without showing stale values.

### 3.6 Error Messages

- [ ] Missing required fields produce clear validation messages.
- [ ] Invalid login credentials produce an appropriate error message.
- [ ] Duplicate registration produces a useful error message.
- [ ] Invalid profile updates are explained clearly.
- [ ] Database or application errors do not expose passwords, secrets, or sensitive database details.
- [ ] Unauthorized access is handled safely.
- [ ] Error messages are understandable and do not reveal unnecessary technical details.

### 3.7 macOS and Windows Compatibility

- [ ] Run the application and tests in a supported macOS environment.
- [ ] Run the application and tests in a supported Windows environment.
- [ ] Confirm the documented Python and dependency versions work on both systems.
- [ ] Verify SQLite database creation and access on both systems.
- [ ] Check file paths and database configuration for operating-system differences.
- [ ] Verify registration, login, profile management, filtering, and interest actions in a browser on both systems.
- [ ] Confirm forms, redirects, and error messages behave consistently.
- [ ] Document any operating-system-specific failures and their resolutions.

## 4. Test Execution and Reporting

For each test, record the result as **Pass**, **Fail**, or **Not Run**.

| Test ID | Result | Notes |
|---|---|---|
| TC-01 | Not Run | |
| TC-02 | Not Run | |
| TC-03 | Not Run | |
| TC-04 | Not Run | |
| TC-05 | Not Run | |
| TC-06 | Not Run | |
| TC-07 | Not Run | |
| TC-08 | Not Run | |
| TC-09 | Not Run | |
| TC-10 | Not Run | |
| TC-11 | Not Run | |
| TC-12 | Not Run | |
| TC-13 | Not Run | |
| TC-14 | Not Run | |

## 5. Completion Criteria

- All MVP functional requirements are mapped to at least one test.
- All applicable functional test cases have been executed.
- Failed tests are documented and reported to the development team.
- Integration checklist items are verified or recorded as not run.
- Testing is performed on supported macOS and Windows environments.
- Results are reviewed before the MVP is considered ready for release.

