# Registration regression diagnosis

> This feature guide records its implementation-stage checks. For current setup,
> full test counts, known limitations, and merge readiness, use the
> [final integration audit](code-and-tests.md).

The reported `205 passed, 1 failed` result belongs to the earlier matching-stage
checkout. On investigation of the current uncommitted local work, the original
`test_password_policy_and_confirmation` passed before any changes in this task.
The profile-onboarding changes had already restored the real registration form.

The older failure was reproduced without replacing workspace files: the archived
HEAD registration template was injected into a temporary test app's Jinja loader,
and the actual existing test was run against that app. Its first failure was:

```text
src/roomie/tests/test_auth_browser.py:142:
    assert f'minlength="{MIN_PASSWORD_LENGTH}"' in html
E   assert 'minlength="8"' in '<!DOCTYPE html>...'
1 failed
```

The archived form had `minlength="12"`, unnamed password controls, and
`data-preview-form`. That identified a real registration-page problem, not an
outdated assertion or a test of an unused preview page. The backend `/register`
route renders this shared template with `auth_enabled=True`. The current local
form correctly selects the API branch, names both password fields, and derives
both minlength attributes from `auth.MIN_PASSWORD_LENGTH` (8).

The current JavaScript handler sends JSON to the form's `/auth/register` action,
includes same-origin cookies and `X-CSRF-Token`, displays actual backend errors,
and follows the existing safe onboarding redirect. SQLite account insertion,
Werkzeug password hashing, sessions, CSRF checks, and redirect policy were not
changed for this investigation. The standalone `src.preview` app still uses the
intentional visual-preview branch; removing it would be incorrect.

Changes in this task:

- `src/templates/register.html`: visible “Use at least 8 characters” guidance,
  derived from the existing backend constant and associated with both password
  inputs through `aria-describedby`.
- `src/roomie/tests/test_auth_browser.py`: an additional parsed-form contract
  test checking the actual POST action, real handler flag, named required password
  fields, both minlength attributes, accessible guidance, and absence of backend
  preview behavior. All original password/security assertions remain intact.
- `tests/browser/profile.mjs`: trusted browser typing checks seven-character
  rejection, eight-character acceptance, confirmation mismatch, registration CSRF
  rejection, successful API registration, wrong-password login, and successful
  login using the exact eight-character password.
- This diagnosis document.

Final verification:

```text
.venv/bin/python -m pytest -q
271 passed in 29.42s

.venv/bin/python tests/browser/run_profile.py
21 browser scenarios passed
```

The Chrome run uses a temporary SQLite database and real requests, with CSRF
enabled. Its local HTTP-only cookie setting is limited to that existing test
harness. The archived-template failure above is an intentional isolated
reproduction, not a remaining failure in the current suite. Matching, profile
storage, interests, and schema code were not modified in this task. Existing
uncommitted work was preserved; nothing was committed, pushed, or merged.
