// All relationship state comes from the existing SQLite-backed interest APIs.
// Never infer mutual interest from a browser flag or store it in browser storage.
(() => {
  const root = document.querySelector('[data-interest-panel], [data-matches-center]');
  if (!root) return;
  const center = root.hasAttribute('data-matches-center');
  const feedback = root.querySelector('[data-interest-feedback]');
  const login = root.querySelector('[data-interest-login]');
  const banner = root.querySelector('[data-mutual-banner]');
  const refreshButton = root.querySelector('[data-interest-refresh]');
  let state = null;
  let busy = false;
  let queuedRefresh = false;

  class RequestError extends Error {
    constructor(message, status) { super(message); this.status = status; }
  }
  const validId = value => Number.isSafeInteger(value) && value > 0;
  const endpointFor = (template, id) => {
    if (!validId(id)) throw new Error('This account or profile is unavailable.');
    const url = new URL(template, window.location.origin);
    url.pathname = url.pathname.replace(/\/0$/, `/${id}`);
    return url.href;
  };
  const request = async (url, method = 'GET') => {
    const options = {method, credentials: 'same-origin', cache: 'no-store'};
    if (method !== 'GET') {
      options.headers = {'Content-Type': 'application/json',
        'X-CSRF-Token': document.querySelector('meta[name="csrf-token"]').content};
      options.body = '{}';
    }
    const response = await fetch(url, options);
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new RequestError(data?.error || 'Unable to complete this request.', response.status);
    if (method === 'GET' && !Array.isArray(data)) throw new Error('Unexpected connection data.');
    return data;
  };
  const readState = async () => {
    const kinds = center ? ['sent', 'received', 'mutual'] : ['sent', 'mutual'];
    const arrays = await Promise.all(kinds.map(kind => request(root.dataset[`${kind}Url`])));
    return Object.fromEntries(kinds.map((kind, index) => [kind, arrays[index]]));
  };
  const element = (tag, className, text) => {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined) node.textContent = text;
    return node;
  };
  const hasSent = userId => state.sent.some(person => person.user_id === userId)
    || state.mutual.some(person => person.user_id === userId);
  const isMutual = userId => state.mutual.some(person => person.user_id === userId);
  const actionButton = (action, id, label) => {
    const button = element('button', action === 'withdraw' ? 'interest-withdraw' : '', label);
    button.type = 'button';
    button.dataset.interestAction = action;
    button.dataset.userId = id;
    return button;
  };
  const addTimestamp = (card, person, kind) => {
    if (typeof person.since !== 'string' || !person.since.trim()) return;
    const prefix = {sent: 'Sent', received: 'Received', mutual: 'Matched'}[kind];
    const line = element('p', 'connection-date', `${prefix} `);
    // SQLite CURRENT_TIMESTAMP uses UTC; never substitute a made-up date.
    const raw = /^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(person.since)
      ? person.since.replace(' ', 'T') + 'Z' : person.since;
    const date = new Date(raw);
    if (Number.isNaN(date.getTime())) line.append(document.createTextNode(person.since));
    else {
      const time = element('time', '', date.toLocaleString(undefined, {
        year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit', timeZoneName: 'short'
      }));
      time.dateTime = date.toISOString();
      line.append(time);
    }
    card.append(line);
  };
  const connectionCard = (person, kind) => {
    const id = person.user_id;
    if (!validId(id)) throw new Error('Unexpected account identifier.');
    const name = (typeof person.name === 'string' && person.name.trim()) || person.username || `User ${id}`;
    const card = element('article', 'connection-card');
    card.dataset.userId = id;
    const heading = element('div', 'connection-identity');
    const avatar = element('span', 'connection-avatar', Array.from(name)[0].toUpperCase());
    avatar.setAttribute('aria-hidden', 'true');
    const identity = element('div');
    identity.append(element('h3', '', name));
    if (person.username) identity.append(element('p', 'connection-username', `@${person.username}`));
    heading.append(avatar, identity);
    card.append(heading);
    if (isMutual(id)) card.append(element('p', 'connection-status', 'Mutual match'));
    addTimestamp(card, person, kind);
    if (validId(person.profile_id)) {
      const link = element('a', 'text-link', 'View profile ↗');
      link.href = endpointFor(root.dataset.profileUrl, person.profile_id);
      card.append(link);
    } else card.append(element('p', 'connection-profile-missing', 'Profile not available yet.'));
    const actions = element('div', 'interest-actions');
    const send = actionButton('send', id, hasSent(id) ? 'Interest sent' : 'Show Interest');
    send.disabled = hasSent(id);
    send.setAttribute('aria-label', `${send.textContent}: ${name}`);
    actions.append(send);
    if (hasSent(id)) {
      const withdraw = actionButton('withdraw', id, 'Withdraw interest');
      withdraw.setAttribute('aria-label', `Withdraw interest: ${name}`);
      actions.append(withdraw);
    }
    card.append(actions);
    return card;
  };
  const render = () => {
    banner.hidden = !state || state.mutual.length === 0;
    root.dataset.loaded = String(state !== null);
    if (!center) {
      const id = Number(root.dataset.userId);
      const sent = state && hasSent(id);
      root.dataset.interestState = !state ? 'unknown' : sent ? 'sent' : 'not-sent';
      root.dataset.mutual = state ? String(isMutual(id)) : 'unknown';
      // A positive confirmation must refer to this specific roommate.
      banner.hidden = !state || !isMutual(id);
      const send = root.querySelector('[data-interest-action="send"]');
      const withdraw = root.querySelector('[data-interest-action="withdraw"]');
      send.textContent = sent ? 'Interest sent' : 'Show Interest';
      send.disabled = !state || sent;
      withdraw.hidden = !sent;
      withdraw.disabled = !state;
      return;
    }
    root.querySelectorAll('[data-connections-section]').forEach(section => {
      const kind = section.dataset.connectionsSection;
      const list = section.querySelector('[data-connections-list]');
      const empty = section.querySelector('[data-section-state]');
      const count = section.querySelector('[data-count]');
      list.replaceChildren();
      count.textContent = state ? `(${state[kind].length})` : '';
      empty.hidden = !!state && state[kind].length > 0;
      if (!state) empty.textContent = 'Connection data is unavailable. Refresh to try again.';
      else if (state[kind].length === 0) empty.textContent = {
        mutual: 'No mutual matches yet. A match appears when you both show interest.',
        sent: 'No interests sent yet. Explore roommates to find your people.',
        received: 'No interests received yet. Check back as more people connect.'
      }[kind];
      else state[kind].forEach(person => list.append(connectionCard(person, kind)));
    });
  };
  const setBusy = value => {
    busy = value;
    root.setAttribute('aria-busy', String(value));
    root.querySelectorAll('button').forEach(button => { button.disabled = value; });
    if (value) banner.hidden = true;
    else render();
  };
  const fail = error => {
    state = null;
    feedback.textContent = error.status === 401
      ? 'Your session has expired. Log in again to manage your connections.'
      : error instanceof RequestError ? error.message
      : 'Unable to reach your connections. Refresh to try again.';
    login.hidden = error.status !== 401;
    render();
  };
  const finish = () => {
    setBusy(false);
    refreshButton.disabled = false;
    if (queuedRefresh) { queuedRefresh = false; void refresh(); }
  };
  const refresh = async () => {
    if (busy) { queuedRefresh = true; return; }
    setBusy(true);
    feedback.textContent = center ? 'Loading your connections…' : 'Checking interest status…';
    try {
      state = await readState();
      login.hidden = true;
      render();
      feedback.textContent = 'Connection status updated.';
    } catch (error) { fail(error); }
    finally { finish(); }
  };
  const mutate = async (id, method) => {
    if (busy || !state || !validId(id)) return;
    setBusy(true);
    feedback.textContent = method === 'POST' ? 'Sending interest…' : 'Withdrawing interest…';
    let acknowledged = false;
    let conflict = false;
    try {
      const url = center ? endpointFor(root.dataset.actionUrl, id) : root.dataset.actionUrl;
      try {
        await request(url, method);
        acknowledged = true;
      } catch (error) {
        // Another tab may already have performed this exact change.
        if ((method === 'POST' && error.status === 409) || (method === 'DELETE' && error.status === 404)) conflict = true;
        else throw error;
      }
      state = await readState();
      login.hidden = true;
      render();
      const sent = hasSent(id);
      feedback.textContent = sent
        ? conflict ? 'Interest was already sent. Status refreshed.' : 'Interest sent.'
        : method === 'DELETE' ? 'Interest withdrawn.' : 'Interest changed in another session. Status refreshed.';
    } catch (error) {
      fail(error);
      if (acknowledged) feedback.textContent = 'Your change was saved, but status could not be refreshed. Refresh before another action.';
    } finally {
      finish();
      if (acknowledged || conflict) window.dispatchEvent(new Event('roomie:interest-changed'));
    }
    // Restore keyboard focus after cards are replaced or the send button disables.
    const selector = `[data-interest-action="${state && hasSent(id) ? 'withdraw' : 'send'}"]`;
    const focusTarget = center
      ? root.querySelector(`${selector}[data-user-id="${id}"]`)
      : root.querySelector(selector);
    (focusTarget && !focusTarget.disabled ? focusTarget : refreshButton).focus();
  };
  root.addEventListener('click', event => {
    const button = event.target.closest('button');
    if (!button || !root.contains(button) || button.disabled) return;
    if (button.hasAttribute('data-interest-refresh')) void refresh();
    else if (button.dataset.interestAction) {
      const id = Number(button.dataset.userId || root.dataset.userId);
      void mutate(id, button.dataset.interestAction === 'send' ? 'POST' : 'DELETE');
    }
  });
  window.addEventListener('roomie:interest-snapshot', event => {
    // Notification refreshes already read the same APIs. Reuse that confirmed
    // snapshot instead of leaving an old mutual card visible or issuing more GETs.
    if (busy) return;
    if (!event.detail) { fail(new RequestError('Log in again.', 401)); return; }
    const focused = document.activeElement;
    const action = focused?.dataset.interestAction;
    const id = Number(focused?.dataset.userId || root.dataset.userId);
    const recovering = !state;
    state = event.detail;
    login.hidden = true;
    render();
    if (recovering) feedback.textContent = 'Connection status updated.';
    if (action && validId(id)) {
      const selector = `[data-interest-action="${hasSent(id) ? 'withdraw' : 'send'}"]`;
      const target = root.querySelector(center ? `${selector}[data-user-id="${id}"]` : selector);
      (target && !target.disabled ? target : refreshButton).focus();
    }
  });
  window.addEventListener('pageshow', event => { if (event.persisted) void refresh(); });
  window.addEventListener('focus', () => { if (!document.hidden) void refresh(); });
  document.addEventListener('visibilitychange', () => { if (!document.hidden) void refresh(); });
  void refresh();
})();
