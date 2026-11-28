// HTML views/prefills use GET /preferences/me's handler on the server.
// Writes use the authenticated JSON API and existing session-bound CSRF.
(() => {
  const form = document.querySelector('[data-preferences-form]');
  if (!form) return;
  const selects = [...form.querySelectorAll('select')];
  const budget = form.elements.namedItem('budget');
  const controls = form.querySelectorAll('select, input, button[type="submit"]');
  const feedback = form.querySelector('.form-feedback');
  const login = form.querySelector('[data-preferences-login]');
  let busy = false;
  let authenticated = true;
  const disable = value => controls.forEach(control => { control.disabled = value; });
  budget.addEventListener('input', () => budget.setCustomValidity(''));
  disable(false);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || !authenticated) return;
    const raw = budget.value.trim();
    // Preserve the full SQLite integer range without rounding through Number.
    // The raw JSON numeric token below is validated digits, never user text.
    let amount = 'null';
    let error = '';
    if (raw) {
      if (!/^\d+$/.test(raw) || BigInt(raw) > 9223372036854775807n) {
        error = 'Enter a nonnegative whole-dollar amount up to 9223372036854775807.';
      } else amount = BigInt(raw).toString();
    } else if (budget.validity.badInput) error = 'Enter a valid whole-dollar amount.';
    budget.setCustomValidity(error);
    if (!form.reportValidity()) {
      feedback.textContent = error || 'Check the highlighted preferences.';
      return;
    }
    const values = Object.fromEntries(selects.map(select => [select.name, select.value || null]));
    const body = JSON.stringify(values).slice(0, -1) + `,"budget":${amount}}`;
    busy = true;
    disable(true);
    form.setAttribute('aria-busy', 'true');
    feedback.textContent = 'Saving your preferences…';
    try {
      const response = await fetch(form.action, {
        method: 'PUT', credentials: 'same-origin',
        headers: {'Content-Type': 'application/json',
          'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content}, body
      });
      const data = await response.json();
      if (response.status === 401) {
        authenticated = false;
        login.hidden = false;
        feedback.textContent = 'Your session has expired. Log in again to save your preferences.';
        return;
      }
      if (!response.ok) {
        feedback.textContent = data.error || 'Unable to save your preferences. Please try again.';
        return;
      }
      feedback.textContent = 'Preferences saved. Opening your preferences…';
      window.location.assign(form.dataset.saveDestination);
    } catch {
      feedback.textContent = 'Unable to reach the server. Your edits are still here; try again.';
    } finally {
      busy = false;
      disable(!authenticated);
      form.removeAttribute('aria-busy');
    }
  });
})();
