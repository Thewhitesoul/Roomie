// Current connections, never an unread/new count. No browser storage or writes.
(() => {
  const root = document.querySelector('[data-notifications]');
  if (!root) return;
  const toggle = root.querySelector('.notification-toggle');
  const panel = root.querySelector('#notification-panel');
  const feedback = root.querySelector('[data-notification-feedback]');
  const refreshButton = root.querySelector('[data-notification-refresh]');
  const badge = root.querySelector('[data-notification-badge]');
  const login = root.querySelector('[data-notification-login]');
  const announcement = document.querySelector('[data-match-announcement]');
  const kinds = ['sent', 'received', 'mutual'];
  const validId = id => Number.isSafeInteger(id) && id > 0;
  let busy = false;
  let queued = false;
  let controller;
  let generation = 0;
  let timer;
  let updatedAt = 0;

  const open = value => {
    panel.hidden = !value;
    toggle.setAttribute('aria-expanded', String(value));
  };
  const listFor = kind => root.querySelector(`[data-notification-${kind}]`);
  const clear = message => {
    root.dataset.loaded = 'false';
    delete root.dataset.pendingCount;
    delete root.dataset.mutualCount;
    badge.hidden = true;
    badge.textContent = '';
    toggle.setAttribute('aria-label', 'Notifications: connection status unavailable');
    if (announcement) {
      announcement.hidden = true;
      announcement.querySelector('[data-match-summary]').textContent = '';
    }
    ['pending', 'mutual'].forEach(kind => {
      root.querySelector(`[data-notification-${kind}-total]`).textContent = '';
      const item = document.createElement('li');
      item.textContent = message;
      listFor(kind).replaceChildren(item);
    });
  };
  const renderList = (kind, people) => {
    const list = listFor(kind);
    list.replaceChildren();
    if (!people.length) {
      const empty = document.createElement('li');
      empty.className = 'notification-empty';
      empty.textContent = kind === 'pending' ? 'No interests yet' : 'No matches yet';
      list.append(empty);
    }
    people.forEach(person => {
      const name = (typeof person.name === 'string' && person.name.trim()) || person.username;
      const item = document.createElement('li');
      item.dataset.notificationUser = person.user_id;
      const identity = document.createElement('p');
      identity.className = 'notification-name';
      identity.textContent = name;
      item.append(identity);
      if (kind === 'mutual') {
        list.append(item);
        return;
      }
      const label = document.createElement('small');
      label.className = 'notification-label';
      label.textContent = 'Interested in you';
      item.append(label);
      if (validId(person.profile_id)) {
        const link = document.createElement('a');
        const url = new URL(root.dataset.profileUrl, location.origin);
        url.pathname = url.pathname.replace(/\/0$/, `/${person.profile_id}`);
        link.href = url.href;
        link.textContent = 'View profile ↗';
        link.setAttribute('aria-label', `View profile: ${name}`);
        item.append(link);
      } else {
        const note = document.createElement('small');
        note.textContent = 'Profile not available yet.';
        item.append(note);
      }
      list.append(item);
    });
  };
  const render = state => {
    // A received request awaits a response only while we have not sent one back.
    // Only the mutual API can produce a positive match announcement.
    const sent = new Set(state.sent.map(person => person.user_id));
    const mutual = new Set(state.mutual.map(person => person.user_id));
    const pending = state.received.filter(person => !sent.has(person.user_id) && !mutual.has(person.user_id));
    const focused = document.activeElement;
    const focusedList = focused?.closest('[data-notification-pending], [data-notification-mutual]');
    const focusedId = focused?.closest('[data-notification-user]')?.dataset.notificationUser;
    renderList('pending', pending);
    renderList('mutual', state.mutual);
    if (focusedList && focusedId) {
      (focusedList.querySelector(`[data-notification-user="${focusedId}"] a`) || refreshButton).focus();
    }
    root.dataset.pendingCount = pending.length;
    root.dataset.mutualCount = state.mutual.length;
    root.dataset.loaded = 'true';
    badge.textContent = String(pending.length);
    badge.hidden = pending.length === 0;
    root.querySelector('[data-notification-pending-total]').textContent = `(${pending.length})`;
    root.querySelector('[data-notification-mutual-total]').textContent = `(${state.mutual.length})`;
    toggle.setAttribute('aria-label', `Notifications: ${pending.length} interested in you, ${state.mutual.length} mutual matches`);
    const count = state.mutual.length;
    if (announcement) {
      const summary = count === 1 ? 'You have 1 mutual match. You both showed interest in connecting.'
        : `You have ${count} mutual matches. You each showed interest in connecting.`;
      const line = announcement.querySelector('[data-match-summary]');
      if (line.textContent !== summary) line.textContent = summary;
      announcement.hidden = count === 0;
    }
  };
  const refresh = async (afterChange = false) => {
    if (busy) { queued = queued || afterChange; return; }
    busy = true;
    const current = ++generation;
    root.setAttribute('aria-busy', 'true');
    refreshButton.disabled = true;
    feedback.textContent = 'Checking your connections…';
    const requestController = new AbortController();
    controller = requestController;
    const timeout = window.setTimeout(() => requestController.abort(), 15000);
    try {
      const arrays = await Promise.all(kinds.map(async kind => {
        const response = await fetch(root.dataset[`${kind}Url`], {
          credentials: 'same-origin', cache: 'no-store', signal: requestController.signal
        });
        if (!response.ok) throw Object.assign(new Error('Unable to load connections.'), {status: response.status});
        const data = await response.json();
        if (!Array.isArray(data) || data.some(person => !validId(person.user_id) || typeof person.username !== 'string')) {
          throw new Error('Unexpected connection data.');
        }
        return data;
      }));
      if (current !== generation || queued) return;
      const state = Object.fromEntries(kinds.map((kind, index) => [kind, arrays[index]]));
      render(state);
      // Keep an open My Matches/detail view consistent with these same API reads.
      window.dispatchEvent(new CustomEvent('roomie:interest-snapshot', {detail: state}));
      login.hidden = true;
      feedback.textContent = '';
      updatedAt = Date.now();
    } catch (error) {
      if (current !== generation) return;
      requestController.abort();
      clear('Connection data is unavailable.');
      login.hidden = error.status !== 401;
      feedback.textContent = error.status === 401
        ? 'Your session has expired. Log in again to see your connections.'
        : 'Unable to check your connections. Refresh to try again.';
      if (error.status === 401) {
        window.clearInterval(timer);
        window.dispatchEvent(new CustomEvent('roomie:interest-snapshot', {detail: null}));
      }
    } finally {
      window.clearTimeout(timeout);
      if (current === generation) {
        busy = false;
        refreshButton.disabled = false;
        root.setAttribute('aria-busy', 'false');
        if (queued) { queued = false; void refresh(); }
      }
    }
  };
  toggle.disabled = false;
  toggle.addEventListener('click', () => {
    open(panel.hidden);
    if (!panel.hidden && Date.now() - updatedAt > 15000) void refresh();
  });
  root.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !panel.hidden) {
      event.preventDefault();
      open(false);
      toggle.focus();
    } else if (event.target === toggle && ['ArrowDown', 'ArrowUp'].includes(event.key)) {
      event.preventDefault();
      open(true);
      const items = panel.querySelectorAll('button:not(:disabled), a:not([hidden])');
      items[event.key === 'ArrowDown' ? 0 : items.length - 1].focus();
    }
  });
  document.addEventListener('click', event => { if (!root.contains(event.target)) open(false); });
  root.addEventListener('focusout', event => {
    if (event.relatedTarget && !root.contains(event.relatedTarget)) open(false);
  });
  refreshButton.addEventListener('click', () => { void refresh(); });
  window.addEventListener('roomie:interest-changed', () => { void refresh(true); });
  const returnToPage = () => { if (!document.hidden) void refresh(); };
  window.addEventListener('focus', returnToPage);
  document.addEventListener('visibilitychange', returnToPage);
  const startPolling = () => {
    window.clearInterval(timer);
    timer = window.setInterval(returnToPage, 60000);
  };
  window.addEventListener('pagehide', () => {
    window.clearInterval(timer);
    generation++;
    controller?.abort();
    busy = false;
    queued = false;
    clear('Checking your connections…');
  });
  window.addEventListener('pageshow', event => {
    if (event.persisted) { startPolling(); returnToPage(); }
  });
  clear('Checking your connections…');
  startPolling();
  void refresh();
})();
