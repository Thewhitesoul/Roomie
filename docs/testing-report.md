# Roomie – Testing and Integration Report


---

## 1. Introduction

The purpose of my work was to test the Roomie application, check whether its features were working as expected, and identify problems that needed to be fixed.

I focused on account registration, login, user profiles, preferences, roommate matching, and other application features.

## 2. My Responsibilities

My main responsibilities included:

- Reviewing project requirements.
- Running automated tests.
- Checking registration and input validation.
- Finding and documenting errors.
- Reviewing connections between the frontend and backend.
- Updating the project's testing documentation.

## 3. Testing Environment

The project was tested using:

- **Operating System:** ChromeOS Linux
- **Programming Language:** Python
- **Backend Framework:** Flask
- **Database:** SQLite
- **Testing Tool:** Pytest
- **Version Control:** Git and GitHub

## 4. Testing Results

### Full Test Run

The complete automated test suite was run to check different parts of the application.

**Command used:**

```bash
PYTHONPATH=src/roomie python -m pytest -v
```

**Results:**
- Total tests: 131
- Passed: 130
- Failed: 1

Most tests passed. One registration test failed because the backend did not handle regular HTML form data as expected.

### Additional Registration Tests

I also added four tests to check different registration situations.

**Test results:**

- Short username: Passed
- Password with minimum 8 characters: Passed
- Number entered instead of email text: Failed
- Database insertion error: Passed

**Summary:** 3 passed, 1 failed.

## 5. Problems Identified

Two registration issues were identified during testing.

**1. Registration form issue**

The registration test using regular form data failed because the backend currently expects JSON data. The team needs to decide how the frontend and backend should communicate.

**2. Incorrect email input**

When a number was entered instead of an email address, the application produced an error instead of returning a proper validation message.

Both issues were documented for the development team to review.

## 6. Frontend and Backend Review

Some frontend pages and buttons still appeared to be previews rather than fully connected features.

Further work is needed to connect and test:

- Registration and login forms.
- User profiles and preferences.
- Roommate matching.
- Interest actions.

These features need additional testing before the application can be considered fully integrated.

## 7. Work Completed

During this milestone, I:

- Ran the automated test suite.
- Added four additional registration tests.
- Reviewed test failures and identified their possible causes.
- Updated `tests/README.md` with testing results.
- Documented issues and suggested improvements.

## 8. Recommendations

The next steps for the team are:

1. Fix the registration input-handling issues.
2. Connect the frontend forms to the backend.
3. Test the main features through the actual application.
4. Run the automated tests again after fixes.
5. Review remaining issues before the final demonstration.

## 9. Conclusion

Testing helped confirm that most of the tested functionality was working and also revealed areas that still need improvement.

The full test run had 130 passing tests and one failure. My four additional registration tests had three passing tests and one failure.

I documented the results and identified issues for the team to address. More testing will be needed after the remaining problems are fixed.


## Cyclomatic Complexity Analysis

Cyclomatic complexity was measured using Radon 6.0.1.

Command used:

`radon cc src/roomie/app -s -a`

Results:
- Total functions and methods analyzed: 41
- Average cyclomatic complexity: 3.80
- Overall complexity grade: A

The majority of functions received Grade A, indicating relatively low complexity. However, three functions were identified for closer review:

- `profile.py` — `_clean`: 33 (Grade E)
- `matches.py` — `find_matches`: 20 (Grade C)
- `preferences.py` — `save_preferences`: 18 (Grade C)

The `_clean` function has the highest complexity and should be reviewed for possible simplification. The other two functions may also benefit from being divided into smaller, more manageable sections.

The analysis output is saved in `docs/cyclomatic-complexity.txt`.
