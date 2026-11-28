// Disclosure navigation: native buttons support Enter/Space; Tab visits links.
const account = document.querySelector('.account-dropdown');
if (account) {
  const toggle = account.querySelector('.account-toggle');
  const links = account.querySelector('.account-links');
  const setOpen = open => {
    toggle.setAttribute('aria-expanded', String(open));
    links.hidden = !open;
  };
  setOpen(false);
  toggle.addEventListener('click', () => setOpen(links.hidden));
  account.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !links.hidden) {
      event.preventDefault();
      setOpen(false);
      toggle.focus();
    }
    if (event.target === toggle && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      setOpen(true);
      const items = links.querySelectorAll('a, button');
      items[event.key === 'ArrowDown' ? 0 : items.length - 1].focus();
    }
  });
  document.addEventListener('click', event => {
    if (!account.contains(event.target)) setOpen(false);
  });
  account.addEventListener('focusout', event => {
    // Disabling the focused logout button during a request must not hide errors.
    if (!account.contains(event.relatedTarget) && !account.querySelector('[aria-busy="true"]')) setOpen(false);
  });
}

/* Progressive enhancement: navigation stays available if JavaScript is off. */
const menu = document.querySelector('.menu-toggle');
const nav = document.querySelector('#main-nav');
if (menu && nav) {
  document.documentElement.classList.add('js');
  menu.hidden = false;
  const closeMenu = () => {
    menu.setAttribute('aria-expanded', 'false');
    nav.classList.remove('is-open');
  };
  menu.addEventListener('click', () => {
    const open = menu.getAttribute('aria-expanded') !== 'true';
    menu.setAttribute('aria-expanded', String(open));
    nav.classList.toggle('is-open', open);
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape' && menu.getAttribute('aria-expanded') === 'true') {
      closeMenu();
      menu.focus();
    }
  });
  const desktop = window.matchMedia('(min-width: 801px)');
  desktop.addEventListener('change', closeMenu);
}

// Authentication uses same-origin JSON APIs and the signed, HttpOnly session.
document.querySelectorAll('[data-auth-form]').forEach(form => {
  const button = form.querySelector('button[type="submit"]');
  const feedback = form.querySelector('.form-feedback');
  const password = form.querySelector('[name="password"]');
  const confirmation = form.querySelector('[name="confirm_password"]');
  const checkPasswords = () => {
    if (confirmation) confirmation.setCustomValidity(
      confirmation.value === password.value ? '' : 'Passwords must match.'
    );
  };
  if (confirmation) {
    password.addEventListener('input', checkPasswords);
    confirmation.addEventListener('input', checkPasswords);
  }
  button.disabled = false;
  let submitting = false;
  form.addEventListener('submit', async event => {
    event.preventDefault();
    checkPasswords();
    if (submitting || !form.reportValidity()) return;
    submitting = true;
    form.setAttribute('aria-busy', 'true');
    button.disabled = true;
    feedback.textContent = 'Submitting…';
    try {
      const payload = Object.fromEntries(new FormData(form));
      payload.next = new URLSearchParams(window.location.search).get('next') || null;
      const response = await fetch(form.action, {
        method: 'POST', credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
        },
        body: JSON.stringify(payload)
      });
      const data = await response.json();
      if (!response.ok) {
        feedback.textContent = data.error || 'Unable to complete this request.';
        return;
      }
      // Never follow an arbitrary redirect, even if an unexpected response supplies one.
      const destination = new URL(data.redirect || '/profile', window.location.origin);
      const allowed = ['/', '/profile', '/profile/setup', '/profile/edit', '/preferences', '/find-roommates', '/my-matches'].includes(destination.pathname)
        || /^\/roommate\/[0-9]+$/.test(destination.pathname);
      const target = destination.origin === window.location.origin && allowed
        ? destination.pathname + destination.search : '/profile';
      feedback.textContent = data.message || 'Signed in. Redirecting…';
      form.reset();
      window.location.assign(target);
    } catch {
      feedback.textContent = 'Unable to reach the server. Check your connection and try again.';
    } finally {
      submitting = false;
      button.disabled = false;
      form.removeAttribute('aria-busy');
    }
  });
});

// My Profile reads and writes only the existing session-protected SQLite API.
const profileForm = document.querySelector('[data-profile-form]');
if (profileForm) {
  const fields = Object.fromEntries(['name', 'age', 'housing_status', 'preferred_location', 'bio', 'interests', 'budget']
    .map(name => [name, profileForm.elements.namedItem(name)]));
  const controls = profileForm.querySelectorAll('input, select, textarea, button[type="submit"]');
  const feedback = profileForm.querySelector('.form-feedback');
  const retry = profileForm.querySelector('[data-profile-retry]');
  const login = profileForm.querySelector('[data-profile-login]');
  let exists = null;
  let busy = false;
  const readProfile = async response => JSON.parse(await response.text(), (key, value, context) => {
    if (key !== 'budget' || typeof value !== 'number') return value;
    // Modern JSON parsers expose the exact numeric token. Older browsers may
    // handle ordinary budgets but must never silently round a large saved one.
    if (context?.source) return context.source;
    if (!Number.isSafeInteger(value)) throw new Error('This browser cannot read this budget precisely.');
    return String(value);
  });
  const disableControls = disabled => controls.forEach(control => { control.disabled = disabled; });
  const populate = data => {
    fields.name.value = data.name;
    fields.preferred_location.value = data.preferred_location;
    fields.bio.value = data.bio;
    fields.interests.value = data.interests.join(', ');
    fields.age.value = data.age ?? '';
    fields.housing_status.value = data.housing_status ?? '';
    fields.budget.value = data.budget ?? '';
  };
  const requireLogin = () => {
    exists = null;
    login.hidden = false;
    feedback.textContent = 'Your session has expired. Log in again to load or save your profile.';
  };
  const load = async () => {
    if (busy) return;
    busy = true;
    exists = null;
    disableControls(true);
    profileForm.setAttribute('aria-busy', 'true');
    retry.hidden = true;
    feedback.textContent = 'Loading your profile…';
    try {
      const response = await fetch(profileForm.dataset.readUrl, {
        credentials: 'same-origin', cache: 'no-store'
      });
      if (response.status === 401) { requireLogin(); return; }
      if (response.status === 404) {
        exists = false;
        feedback.textContent = 'Create your profile below.';
        return;
      }
      const data = await readProfile(response);
      if (!response.ok) throw new Error(data.error || 'Unable to load your profile.');
      populate(data);
      exists = true;
      feedback.textContent = 'Your saved profile is ready to edit.';
    } catch {
      feedback.textContent = 'Unable to load your profile. Retry before editing so saved information is not overwritten.';
      retry.hidden = false;
    } finally {
      busy = false;
      disableControls(exists === null);
      profileForm.removeAttribute('aria-busy');
    }
  };
  fields.name.addEventListener('input', () => fields.name.setCustomValidity(''));
  fields.interests.addEventListener('input', () => fields.interests.setCustomValidity(''));
  fields.preferred_location.addEventListener('input', () => fields.preferred_location.setCustomValidity(''));
  fields.budget.addEventListener('input', () => fields.budget.setCustomValidity(''));
  retry.addEventListener('click', load);
  profileForm.addEventListener('submit', async event => {
    event.preventDefault();
    if (busy || exists === null) return;
    const interests = fields.interests.value.split(',').map(value => value.trim()).filter(Boolean);
    const interestError = interests.length > 10 || interests.some(value => Array.from(value).length > 30)
      ? 'Use up to 10 interests, with no more than 30 characters each.' : '';
    fields.interests.setCustomValidity(interestError);
    fields.name.setCustomValidity(fields.name.value.trim() ? '' : 'Enter a display name.');
    fields.preferred_location.setCustomValidity(fields.preferred_location.value.trim() ? '' : 'Enter a preferred location.');
    const rawBudget = fields.budget.value.trim();
    let budgetToken = 'null';
    let budgetError = '';
    if (rawBudget) {
      if (!/^\d+$/.test(rawBudget) || BigInt(rawBudget) > 9223372036854775807n) {
        budgetError = 'Enter a nonnegative whole-dollar budget within the SQLite integer range.';
      } else budgetToken = BigInt(rawBudget).toString();
    } else if (fields.budget.validity.badInput) budgetError = 'Enter a valid whole-dollar budget.';
    fields.budget.setCustomValidity(budgetError);
    if (!profileForm.reportValidity()) {
      feedback.textContent = interestError || budgetError || 'Check the highlighted profile fields.';
      return;
    }
    const payload = {
      name: fields.name.value.trim(), preferred_location: fields.preferred_location.value.trim(),
      bio: fields.bio.value.trim(), interests, age: Number(fields.age.value),
      housing_status: fields.housing_status.value
    };
    const creating = !exists;
    busy = true;
    disableControls(true);
    profileForm.setAttribute('aria-busy', 'true');
    feedback.textContent = 'Saving your profile…';
    try {
      const response = await fetch(creating ? profileForm.dataset.createUrl : profileForm.dataset.updateUrl, {
        method: creating ? 'POST' : 'PUT', credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content
        }, body: JSON.stringify(payload).slice(0, -1) + `,"budget":${budgetToken}}`
      });
      if (response.status === 401) { requireLogin(); return; }
      const data = await readProfile(response);
      if (!response.ok) {
        feedback.textContent = data.error || 'Unable to save your profile. Please try again.';
        if (response.status === 409) feedback.textContent += ' Reload to load the saved profile before editing.';
        return;
      }
      populate(data);
      exists = true;
      feedback.textContent = 'Profile saved. Opening your profile…';
      window.location.assign(profileForm.dataset.saveDestination);
    } catch {
      feedback.textContent = 'Unable to reach the server. Your edits are still here; check your connection and try again.';
    } finally {
      busy = false;
      disableControls(exists === null);
      profileForm.removeAttribute('aria-busy');
    }
  });
  load();
}

// Preview forms deliberately make no request and write no browser storage.
document.querySelectorAll('[data-preview-form]').forEach(form => {
  const password = form.querySelector('#password');
  const confirmation = form.querySelector('#confirm_password');
  const checkPasswords = () => {
    if (confirmation) confirmation.setCustomValidity(
      confirmation.value === password.value ? '' : 'Passwords must match.'
    );
  };
  if (confirmation) {
    password.addEventListener('input', checkPasswords);
    confirmation.addEventListener('input', checkPasswords);
  }
  form.addEventListener('submit', event => {
    event.preventDefault();
    form.querySelector('.form-feedback').textContent =
      'Preview only — nothing was submitted or saved. This action will be available when the backend is connected.';
  });
  form.querySelectorAll('button[type="submit"]').forEach(button => { button.disabled = false; });
});
