# Tests

# Roomie Requirements-Based Testing and Integration Plan

## 1. Purpose

This document defines the initial testing and integration plan for the Roomie semester MVP. It translates the requirements in `docs/requirements.md` into testable checks and gives the team a consistent process for reviewing features before they are merged into `main`.

## 2. Scope
The plan covers the MVP requirements FR-01 through FR-11:

- Account registration, login, and logout
- Roommate profile creation and editing
- Lifestyle, interest, housing-need, and preference data
- Required-field validation
- Roommate filtering and discovery
- Safe profile display
- Adding, changing, and removing interest
- Prevention of self-interest
- Protection of authenticated pages

Room listings, messaging, reporting, payments, verification, and other full-system features are outside the MVP test scope.

## 3. Test Environment
- Python and Flask application
- SQLite database
- pytest for automated tests
- Manual browser testing in Chrome, Firefox, Edge, and Safari when available
- macOS and Windows development environments
- A separate temporary SQLite database for automated testing
- Seeded test accounts and profiles that contain no real personal information

Local development databases must not be used for automated tests. Tests must not depend on execution order and should reset their data before each run.

## 4. Requirements Traceability

| Requirement | Test objective | Test type | Expected result |
| --- | --- | --- | --- |
| FR-01 | Submit valid and invalid registration information. | Automated and manual | A valid account is created once. Missing or duplicate required data is rejected clearly. |
| FR-02 | Log in with correct and incorrect credentials, then log out. | Automated and manual | Correct credentials create a session. Incorrect credentials fail without revealing whether an account exists. Logout ends the session. |
| FR-03 | Create and edit a profile while authenticated. | Automated and manual | Saved profile information is displayed correctly and later edits replace the intended values. |
| FR-04 | Save interests, lifestyle information, housing needs, and preferences. | Automated | All supported fields persist and remain connected to the correct user. |
| FR-05 | Submit each required profile field as empty. | Automated and manual | The request is rejected, the missing field is identified, and no partial record is stored. |
| FR-06 | Filter seeded profiles using selected preferences. | Automated and manual | Only profiles satisfying the supported filters are returned. |
| FR-07 | View another roommate profile. | Automated and manual | Relevant profile data is visible, but email, password hash, and private login data are not exposed. |
| FR-08 | Show interest in another user. | Automated | One valid interest record connects the authenticated sender and selected receiver. |
| FR-09 | Change and remove existing interest. | Automated | The correct record changes or is removed without affecting another user's records. |
| FR-10 | Attempt to show interest in the authenticated user's own profile. | Automated | The request is rejected and no self-interest record is stored. |
| FR-11 | Open protected profile and matching pages without a session. | Automated and manual | The user is redirected to login or receives the intended unauthorized response. |

## 5. Nonfunctional Tests

### Performance

- Measure normal page requests during team testing. At least 95 percent should complete within three seconds.
- Seed 500 profiles and confirm a supported match search completes within two seconds.
- Confirm every submitted form displays success or error feedback.

### Reliability

- Confirm invalid input does not create partial account or profile records.
- Confirm a failed database write is rolled back.
- Run all critical automated tests before the MVP demonstration.
- Record failed tests and defects in Trello with reproduction steps and an owner.

### Security and Privacy

- Confirm passwords are stored as hashes and never displayed or logged as plain text.
- Confirm protected routes reject unauthenticated requests.
- Confirm SQL operations use parameterized queries.
- Test length limits, unexpected values, and common unsafe characters in user-controlled input.
- Confirm secret keys, virtual environments, and SQLite files are excluded from commits.
- Confirm login errors do not reveal whether an account exists.

### Interface and Compatibility

- Test at approximately 360-pixel and 1280-pixel viewport widths.
- Confirm required form fields have visible labels.
- Complete registration, profile, preference, and matching actions with keyboard navigation.
- Confirm error messages identify the field or action that needs correction.
- Perform browser checks on the current team versions of Chrome, Firefox, Edge, and Safari when available.

## 6. Integration Process

1. Pull the latest `main` before starting work.
2. Implement or test one focused feature on a separate branch.
3. Run the related automated tests locally.
4. Run the critical test suite against a temporary SQLite database.
5. Manually test the affected user workflow in a browser.
6. Open a pull request and describe the requirement IDs covered.
7. Review the changed code, test results, and database effects.
8. Fix failures on the feature branch and rerun tests.
9. Merge only after the reviewer confirms that critical tests pass and the change does not expose secrets or local database files.

## 7. Defect Reporting

Each defect should include:

- Short title
- Related requirement ID
- Test environment and browser
- Steps to reproduce
- Expected result
- Actual result
- Severity: critical, major, normal, or minor
- Screenshot or error output when useful
- Assigned owner and retest status

A critical defect blocks login, corrupts or exposes data, bypasses authentication, or prevents the main MVP workflow. Critical defects must be fixed before the MVP demonstration.

## 8. Entry and Exit Criteria

Testing may begin when the requirement being tested has an implemented route or interface and a repeatable setup process. A feature is ready for review when:

- Its requirement-based tests pass
- No critical or major defect remains open
- Invalid input is handled without partial data
- Authentication and privacy checks pass where applicable
- Manual browser behavior matches the requirement
- Setup or test instructions are updated
- The pull request identifies the requirement IDs tested

## 9. Current Dependencies

The test cases and traceability plan can be prepared before backend implementation is complete. Final automated integration tests depend on stable Flask routes, SQLite schema, validation rules, and service behavior. Rajju should edit the test names and commands to match the final implementation rather than assuming draft function names.
