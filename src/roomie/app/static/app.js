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
    if (!account.contains(event.relatedTarget)) setOpen(false);
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
const interest = document.querySelector('[data-interest]');
if (interest) {
  interest.hidden = false;
  interest.setAttribute('aria-describedby', 'interest-feedback');
  interest.addEventListener('click', () => {
    document.querySelector('#interest-feedback').textContent =
      'Preview only — your interest was not sent or saved. Connecting with roommates requires the backend.';
  });
}
