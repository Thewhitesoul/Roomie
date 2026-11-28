// Actual browser requests, rendered forms, session cookies, CSRF, and SQLite.
// No mock fetch, authentication flags, or browser storage are used.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {mkdtemp, readFile, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {setTimeout as sleep} from 'node:timers/promises';

const base = process.argv[2];
if (!base) throw new Error('Run through tests/browser/run_profile.py');
const directory = await mkdtemp(join(tmpdir(), 'roomie-chrome-profile-'));
const chrome = spawn(process.env.ROOMIE_CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', [
  '--headless', '--no-first-run', '--no-default-browser-check', '--disable-background-networking',
  '--disable-extensions', '--use-mock-keychain', '--remote-debugging-port=0',
  `--user-data-dir=${directory}`, 'about:blank'
], {stdio: 'ignore'});
chrome.on('error', error => { console.error(error.message); });
let ws;
let count = 0;
try {
  let connection;
  for (let i = 0; i < 100; i++) {
    try { connection = (await readFile(join(directory, 'DevToolsActivePort'), 'utf8')).trim().split('\n'); break; }
    catch { await sleep(100); }
  }
  assert(connection, 'Chrome must start and expose its debugging port');
  ws = new WebSocket(`ws://127.0.0.1:${connection[0]}${connection[1]}`);
  await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
  let id = 0;
  const pending = new Map();
  ws.onmessage = event => {
    const data = JSON.parse(event.data);
    if (!data.id) return;
    const callbacks = pending.get(data.id);
    if (!callbacks) return;
    pending.delete(data.id);
    clearTimeout(callbacks.timer);
    if (data.error) callbacks.reject(new Error(JSON.stringify(data.error)));
    else callbacks.resolve(data.result);
  };
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const key = ++id;
    const timer = setTimeout(() => { pending.delete(key); reject(new Error(`CDP timeout: ${method}`)); }, 10000);
    pending.set(key, {resolve, reject, timer});
    ws.send(JSON.stringify({id: key, method, params, ...(sessionId ? {sessionId} : {})}));
  });
  const target = await send('Target.createTarget', {url: 'about:blank'});
  const {sessionId} = await send('Target.attachToTarget', {targetId: target.targetId, flatten: true});
  const cdp = (method, params) => send(method, params, sessionId);
  await cdp('Page.enable');
  await cdp('Runtime.enable');
  await cdp('Page.bringToFront');
  await cdp('Emulation.setFocusEmulationEnabled', {enabled:true});
  const evaluate = async expression => {
    const result = await cdp('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const wait = async expression => {
    for (let i = 0; i < 100; i++) {
      try { if (await evaluate(expression)) return; } catch { /* Navigation replaces the JS context. */ }
      await sleep(100);
    }
    throw new Error(`Browser condition timed out: ${expression}`);
  };
  const navigate = async path => {
    await cdp('Page.navigate', {url: base + path});
    await wait(`location.pathname === ${JSON.stringify(path.split('?')[0])} && document.readyState === 'complete'`);
  };
  const fill = async values => {
    await evaluate(`(() => { for (const [name, value] of Object.entries(${JSON.stringify(values)})) {
      const element = document.querySelector('[name="' + name + '"]');
      element.value = value; element.dispatchEvent(new Event('input', {bubbles:true}));
    } })()`);
  };
  const submit = selector => evaluate(`document.querySelector(${JSON.stringify(selector)}).requestSubmit()`);
  const ready = () => wait(`!!document.querySelector('[data-profile-form]') && !document.querySelector('[data-profile-form] [type="submit"]').disabled`);
  const api = expression => evaluate(expression);
  const pass = message => { count++; console.log(`PASS ${count}: ${message}`); };

  if (!process.argv.includes('--matching-only')) {
    await cdp('Emulation.setDeviceMetricsOverride', {width:1440, height:1000, deviceScaleFactor:1, mobile:false});
    await cdp('Page.navigate', {url:base + '/profile/edit'});
    await wait(`location.pathname === '/login' && document.readyState === 'complete'`);
    assert.equal(await api(`fetch('/profiles/me').then(r => r.status)`), 401);
    pass('anonymous overview/setup/edit data is protected by the existing session');

    await navigate('/register');
    await fill({username:'browser_profile', email:'browser_profile@washburn.edu'});
    // Trusted browser typing makes native minlength validation observable.
    for (const name of ['password','confirm_password']) {
      await evaluate(`document.querySelector('[name="${name}"]').focus()`);
      await cdp('Input.insertText', {text:'seven77'});
    }
    assert.equal(await evaluate(`document.querySelector('[name="password"]').validity.tooShort`),true);
    await submit('[data-auth-form]');
    assert.equal(await evaluate('location.pathname'),'/register');
    assert.equal(await api(`fetch('/auth/me').then(r => r.status)`),401);
    pass('registration rejects seven characters without creating an authenticated session');

    await fill({password:'',confirm_password:''});
    await evaluate(`document.querySelector('[name="password"]').focus()`);
    await cdp('Input.insertText',{text:'Eight123'});
    await evaluate(`document.querySelector('[name="confirm_password"]').focus()`);
    await cdp('Input.insertText',{text:'Other123'});
    await submit('[data-auth-form]');
    assert.equal(await evaluate(`document.querySelector('[name="confirm_password"]').validity.customError`),true);
    await fill({confirm_password:''});
    await evaluate(`document.querySelector('[name="confirm_password"]').focus()`);
    await cdp('Input.insertText',{text:'Eight123'});
    assert.equal(await evaluate(`document.querySelector('section form').checkValidity()`),true);
    assert.equal(await evaluate(`document.querySelector('#registration-password-help').textContent`),'Use at least 8 characters.');
    pass('exactly eight characters meet the unchanged rule; matching confirmation is required');

    await evaluate(`window.registrationCsrf = document.querySelector('meta[name="csrf-token"]').content;
      document.querySelector('meta[name="csrf-token"]').content = 'invalid';`);
    await submit('[data-auth-form]');
    await wait(`document.querySelector('section .form-feedback').textContent.includes('security token')`);
    assert.equal(await api(`fetch('/auth/me').then(r => r.status)`),401);
    await evaluate(`document.querySelector('meta[name="csrf-token"]').content = window.registrationCsrf;`);
    pass('registration enforces CSRF before creating an account or session');
    await submit('[data-auth-form]');
    await wait(`location.pathname === '/profile/setup' && document.readyState === 'complete'`);
    await ready();
    assert.equal(await evaluate(`document.querySelector('[name="name"]').value`), '');
    assert.equal(await api(`fetch('/profiles/me').then(r => r.status)`), 404);
    assert.equal(await evaluate(`document.querySelector('[name="age"]').required && document.querySelector('[name="housing_status"]').required`), true);
    pass('real registration authenticates and opens setup, without fabricating a profile');

    await fill({name:'  Browser User  ', age:'21', housing_status:'needs_housing', preferred_location:'  Topeka  ', bio:'  Initial bio  ', interests:' Cooking, , Hiking, Cooking,  ', budget:'700'});
    await submit('[data-profile-form]');
    await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
    let saved = await api(`fetch('/profiles/me').then(r => r.json())`);
    assert.equal(saved.name, 'Browser User');
    assert.equal(saved.age, 21);
    assert.equal(saved.housing_status, 'needs_housing');
    assert.equal(saved.preferred_location, 'Topeka');
    assert.equal(saved.budget, 700);
    assert.deepEqual(saved.interests, ['cooking','hiking']);
    const profileId = saved.id;
    assert.equal(await evaluate(`!!document.querySelector('[data-profile-form]')`), false);
    assert.equal(await evaluate(`document.querySelector('.profile-avatar').textContent`), 'B');
    assert.equal(await evaluate(`document.querySelector('.account-toggle span').textContent`), 'Browser User');
    assert((await evaluate('document.body.textContent')).includes('Profile created.'));
    pass('setup saves required fields/budget/interests and opens a read-only profile with chosen display name');

    await navigate('/profile/edit');
    await ready();
    for (const [name,value] of Object.entries({name:'Browser User',age:'21',housing_status:'needs_housing',preferred_location:'Topeka',bio:'Initial bio',interests:'cooking, hiking',budget:'700'})) {
      assert.equal(await evaluate(`document.querySelector('[name="${name}"]').value`), value);
    }
    await fill({name:'Cancelled name', age:'99', bio:'Must not save'});
    await evaluate(`document.querySelector('.profile-form-actions a').click()`);
    await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
    assert.deepEqual(await api(`fetch('/profiles/me').then(r => r.json())`), saved);
    pass('edit is prefilled and Cancel returns to the overview without changing SQLite');

    await navigate('/profile/edit');
    await ready();
    await fill({name:'Updated User',age:'22',housing_status:'has_housing',bio:'Updated bio',interests:' reading, , music ',budget:'750'});
    await submit('[data-profile-form]');
    await wait(`location.pathname === '/profile' && document.querySelector('#display-name')?.textContent === 'Updated User'`);
    saved = await api(`fetch('/profiles/me').then(r => r.json())`);
    assert.equal(saved.id, profileId);
    assert.equal(saved.age,22);
    assert.equal(saved.budget,750);
    assert.equal(saved.housing_status,'has_housing');
    assert.deepEqual(saved.interests,['reading','music']);
    assert((await evaluate('document.body.textContent')).includes('Profile saved.'));
    pass('editing uses PUT on the same profile and shows saved changes and real success feedback');

    for (const budget of ['9007199254740993','9223372036854775807']) {
      await navigate('/profile/edit');await ready();
      await fill({budget});await submit('[data-profile-form]');
      await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
      assert((await api(`fetch('/profiles/me',{cache:'no-store'}).then(r=>r.text())`)).includes(budget));
      assert((await evaluate(`document.querySelector('.profile-content').textContent`)).includes('$'+budget+'/month'));
      await navigate('/profile/edit');await ready();
      assert.equal(await evaluate(`document.querySelector('[name="budget"]').value`),budget);
      await submit('[data-profile-form]');
      await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
      assert((await api(`fetch('/profiles/me',{cache:'no-store'}).then(r=>r.text())`)).includes(budget));
    }
    await navigate('/profile/edit');await ready();await fill({budget:'750'});
    await submit('[data-profile-form]');
    await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
    pass('profile budgets above JavaScript’s safe range and at SQLite’s maximum save and reload without rounding');

    for (const width of [1440,768,360]) {
      await cdp('Emulation.setDeviceMetricsOverride', {width,height:1000,deviceScaleFactor:1,mobile:width < 800});
      assert.equal(await evaluate('document.documentElement.scrollWidth'),width);
      const toggle = `document.querySelector('.account-toggle')`;
      await evaluate(`${toggle}.focus()`);
      await cdp('Input.dispatchKeyEvent', {type:'keyDown',key:'Enter',code:'Enter',windowsVirtualKeyCode:13,text:'\r'});
      await cdp('Input.dispatchKeyEvent', {type:'keyUp',key:'Enter',code:'Enter',windowsVirtualKeyCode:13});
      await wait(`${toggle}.getAttribute('aria-expanded') === 'true'`);
      await cdp('Input.dispatchKeyEvent', {type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      await cdp('Input.dispatchKeyEvent', {type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
      await wait(`${toggle}.getAttribute('aria-expanded') === 'false'`);
      assert.equal(await evaluate(`document.activeElement === ${toggle}`),true);
      const shot = await cdp('Page.captureScreenshot', {format:'png',captureBeyondViewport:true});
      await writeFile(join(tmpdir(),`roomie-profile-overview-${width}.png`), Buffer.from(shot.data,'base64'));
    }
    pass('read-only sections and account menu work at desktop/tablet/mobile widths');

    await navigate('/profile/edit');
    await ready();
    assert.equal(await evaluate('document.documentElement.scrollWidth'),360);
    await fill({interests:Array.from({length:11}, (_,i) => `interest${i}`).join(',')});
    await submit('[data-profile-form]');
    assert.equal(await evaluate(`document.querySelector('[name="interests"]').validity.customError`),true);
    await fill({interests:'x'.repeat(31)});
    await submit('[data-profile-form]');
    assert.equal(await evaluate(`document.querySelector('[name="interests"]').validity.customError`),true);
    await fill({interests:'reading',age:'17'});
    assert.equal(await evaluate(`document.querySelector('[name="age"]').validity.rangeUnderflow`),true);
    await fill({age:'121'});
    assert.equal(await evaluate(`document.querySelector('[name="age"]').validity.rangeOverflow`),true);
    await fill({age:'22',budget:'700.5'});
    assert.equal(await evaluate(`document.querySelector('[name="budget"]').validity.stepMismatch`),true);
    await fill({budget:'750'});
    await evaluate(`document.querySelector('[name="name"]').removeAttribute('maxlength')`);
    await fill({name:'n'.repeat(61)});
    await submit('[data-profile-form]');
    await wait(`document.querySelector('[data-profile-form] .form-feedback').textContent.includes('60')`);
    assert.equal(await evaluate(`document.querySelector('[name="name"]').value.length`),61);
    assert.equal(await api(`fetch('/profiles/me').then(r => r.json()).then(p => p.name)`),'Updated User');
    pass('client and real server validation reject invalid fields without losing edits or overwriting data');

    await fill({name:'Unsaved CSRF edit'});
    await evaluate(`window.originalCsrf = document.querySelector('meta[name="csrf-token"]').content;
      document.querySelector('meta[name="csrf-token"]').content = 'invalid';`);
    await submit('[data-profile-form]');
    await wait(`document.querySelector('[data-profile-form] .form-feedback').textContent.includes('security token')`);
    assert.equal(await evaluate(`document.querySelector('[name="name"]').value`),'Unsaved CSRF edit');
    assert.equal(await api(`fetch('/profiles/me').then(r => r.json()).then(p => p.name)`),'Updated User');
    pass('CSRF protection remains enabled and failed writes preserve entered values');

    await cdp('Network.enable');
    await cdp('Network.setBlockedURLs',{urls:[base + '/profiles/me']});
    await navigate('/profile/edit');
    await wait(`!document.querySelector('[data-profile-retry]').hidden`);
    assert.equal(await evaluate(`document.querySelector('[data-profile-form] [type="submit"]').disabled`),true);
    await cdp('Network.setBlockedURLs',{urls:[]});
    await evaluate(`document.querySelector('[data-profile-retry]').click()`);
    await ready();
    assert.equal(await evaluate(`document.querySelector('[name="name"]').value`),'Updated User');
    pass('failed profile read locks saving until a successful retry restores saved data');

    assert.equal(await api(`fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json',
      'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:'{}'}).then(r => r.status)`),200);
    await api(`fetch('/auth/csrf').then(r => r.json()).then(d => {document.querySelector('meta[name="csrf-token"]').content=d.csrf_token;})`);
    await fill({name:'Cannot save anonymously'});
    await submit('[data-profile-form]');
    await wait(`!document.querySelector('[data-profile-login]').hidden`);
    assert.equal(await api(`fetch('/profiles/me').then(r => r.status)`),401);
    await navigate('/login?next=/profile/edit');
    await fill({email:'browser_profile@washburn.edu',password:'Incorrect123'});
    await submit('section [data-auth-form]');
    await wait(`document.querySelector('section .form-feedback').textContent.includes('Invalid email or password.')`);
    assert.equal(await api(`fetch('/auth/me').then(r => r.status)`),401);
    pass('incorrect login shows the real API error and leaves the user unauthenticated');
    await fill({email:'browser_profile@washburn.edu',password:'Eight123'});
    await submit('section [data-auth-form]');
    await wait(`location.pathname === '/profile/edit' && !!document.querySelector('[data-profile-form]')`);
    await ready();
    pass('expired sessions cannot save; completed-profile login returns to the safe intended editor');

    await submit('.account-links [data-auth-form]');
    await wait(`location.pathname === '/' && !document.querySelector('.account-toggle')`);
    await navigate('/login');
    await fill({email:'browser_legacy@washburn.edu',password:'password123'});
    await submit('section [data-auth-form]');
    await wait(`location.pathname === '/profile/setup' && !!document.querySelector('[data-profile-form]')`);
    await ready();
    for (const [name,value] of Object.entries({name:'Legacy Browser',age:'29',housing_status:'',preferred_location:'Lawrence',bio:'Preserved biography',interests:'music',budget:'0'})) {
      assert.equal(await evaluate(`document.querySelector('[name="${name}"]').value`),value);
    }
    const legacyId = await api(`fetch('/profiles/me').then(r => r.json()).then(p => p.id)`);
    await fill({housing_status:'needs_housing'});
    await submit('[data-profile-form]');
    await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
    assert.equal(await api(`fetch('/profiles/me').then(r => r.json()).then(p => p.id)`),legacyId);
    await submit('.account-links [data-auth-form]');
    await wait(`location.pathname === '/' && !document.querySelector('.account-toggle')`);
    await navigate('/login');
    await fill({email:'browser_legacy@washburn.edu',password:'password123'});
    await submit('section [data-auth-form]');
    await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
    await cdp('Page.navigate', {url:base + '/profile/setup'});
    await wait(`location.pathname === '/profile' && !!document.querySelector('.profile-overview')`);
    pass('legacy profiles prefill every saved field, complete by updating the original ID, and skip setup on later logins');
  }

  await navigate('/');
  // Seed additional accounts only through real JSON APIs. Deliberately create
  // a user without a profile so later profile IDs differ from user IDs.
  const newUser = async (username, fields) => api(`(async () => {
    const getToken = async () => (await (await fetch('/auth/csrf')).json()).csrf_token;
    await fetch('/auth/logout', {method:'POST', headers:{'Content-Type':'application/json',
      'X-CSRF-Token':await getToken()}, body:'{}'});
    const auth = await fetch('/auth/register', {method:'POST', headers:{'Content-Type':'application/json',
      'X-CSRF-Token':await getToken()}, body:JSON.stringify({username:${JSON.stringify(username)},
        email:${JSON.stringify(username + '@washburn.edu')}, password:'password123'})});
    if (auth.status !== 201) throw new Error('Unable to create browser fixture account');
    if (${JSON.stringify(fields)} === null) return (await auth.json()).user;
    const result = await fetch('/profiles', {method:'POST', headers:{'Content-Type':'application/json',
      'X-CSRF-Token':await getToken()}, body:JSON.stringify({age:21,housing_status:'needs_housing',preferred_location:'Topeka',...${JSON.stringify(fields)}})});
    if (result.status !== 201) throw new Error('Unable to create browser fixture profile');
    return result.json();
  })()`);
  const gap = await newUser('matching_gap', null);
  const first = await newUser('matching_first', {name:'First Match', preferred_location:'MatchTown',
    bio:'A real saved bio.', budget:600, interests:['cooking','gaming']});
  const second = await newUser('matching_second', {name:'Second Match', preferred_location:'MatchTown',
    bio:'Another saved bio.', budget:900, interests:['cooking']});
  const unsafeName = '<img src=x onerror=window.pwned=1>';
  const unsafe = await newUser('matching_untrusted', {name:unsafeName, preferred_location:'Elsewhere',
    bio:'<script>window.pwned=1</script>', interests:['<b>reading</b>']});
  const self = await newUser('matching_self', {name:'Own Match Profile', preferred_location:'MatchTown',
    interests:['cooking','gaming']});
  await navigate('/find-roommates');
  const expected = await api(`fetch('/matches').then(r => r.json())`);
  const cardIds = () => evaluate(`[...document.querySelectorAll('.profile-card')].map(el => Number(el.dataset.profileId))`);
  assert.deepEqual(await cardIds(), expected.map(p => p.id));
  assert.deepEqual(expected.slice(0,2).map(p => p.id), [first.id, second.id]);
  assert(!expected.some(p => p.id === self.id));
  assert.notEqual(first.id, first.user_id);
  assert.equal(await evaluate(`document.querySelector('.profile-card h2').textContent`), 'First Match');
  pass('real matching page preserves API ranking and excludes own profile');

  const rejected = await api(`(async () => {
    const requests=[['/matches?max_budget='+encodeURIComponent('²'),'GET'],
      ['/matches?min_budget=9223372036854775808','GET'],
      ['/find-roommates?max_budget='+encodeURIComponent('²'),'GET'],
      ['/profiles/9223372036854775808','GET'],['/roommate/'+('9'.repeat(4400)),'GET'],
      ['/preferences/profile/9223372036854775808','GET'],['/interest/9223372036854775808','POST']];
    const statuses=[];
    for(const [url,method] of requests) {
      const options={method};if(method==='POST') {
        options.headers={'Content-Type':'application/json','X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content};options.body='{}';
      }
      statuses.push((await fetch(url,options)).status);
    }
    return statuses;
  })()`);
  assert.deepEqual(rejected,[400,400,400,404,404,404,404]);
  assert.equal(await api(`fetch('/profiles/me').then(r=>r.headers.get('Cache-Control'))`),'no-store');
  pass('malformed/overflow numeric inputs return controlled errors and authenticated JSON is marked no-store');

  assert.equal(await evaluate(`document.querySelector('.profile-grid img') === null && window.pwned === undefined`), true);
  assert((await evaluate(`document.querySelector('.profile-grid').textContent`)).includes(unsafeName));
  pass('untrusted profile content renders as text without executing HTML');

  await fill({min_budget:'500', max_budget:'700', location:'MatchTown', interests:' cooking, gaming '});
  await submit('.match-filters');
  await wait(`location.search.includes('interest=cooking') && document.readyState === 'complete' && document.querySelectorAll('.profile-card').length === 1`);
  assert.deepEqual(await cardIds(), [first.id]);
  assert.deepEqual(await evaluate(`new URLSearchParams(location.search).getAll('interest')`), ['cooking','gaming']);
  assert.equal(await evaluate(`document.querySelector('[name="max_budget"]').value`), '700');
  pass('budget range, location, and comma-separated interest filters work together');

  await evaluate(`document.querySelector('.profile-card a').click()`);
  await wait(`location.pathname === '/roommate/${first.id}' && document.readyState === 'complete'`);
  assert.equal(await evaluate(`document.querySelector('.detail-copy h1').textContent`), 'First Match');
  assert((await evaluate(`document.querySelector('.detail-copy').textContent`)).includes('$600/month'));
  await wait(`document.querySelector('[data-interest-panel]')?.dataset.loaded === 'true'`);
  assert.equal(await evaluate(`document.querySelector('[data-interest-action="send"]').disabled`), false);
  assert.equal(await evaluate(`document.querySelector('[data-interest-panel]').dataset.userId`), String(first.user_id));
  assert.deepEqual(await api(`fetch('/interest/sent').then(r => r.json())`), []);
  pass('card opens by profile ID, targets the correct user for interest, and never sends on page load');

  await navigate('/find-roommates');
  await fill({location:'No such place'});
  await submit('.match-filters');
  await wait(`document.readyState === 'complete' && !!document.querySelector('.empty-state')`);
  assert.deepEqual(await cardIds(), []);
  assert((await evaluate(`document.querySelector('.empty-state').textContent`)).includes('No roommates match'));
  await evaluate(`document.querySelector('.empty-state a').click()`);
  await wait(`document.readyState === 'complete' && document.querySelectorAll('.profile-card').length > 0`);
  for (const width of [1440,768,360]) {
    await cdp('Emulation.setDeviceMetricsOverride', {width, height:900, deviceScaleFactor:1, mobile:width < 800});
    if (await evaluate('document.documentElement.scrollWidth') !== width) {
      console.log('Overflow diagnostics:', await evaluate(`JSON.stringify([...document.querySelectorAll('body *')].map(el => ({
        tag:el.tagName, cls:el.className, text:el.textContent.slice(0,60), left:el.getBoundingClientRect().left,
        right:el.getBoundingClientRect().right, width:el.getBoundingClientRect().width
      })).filter(el => el.right > ${width} || el.left < 0))`));
    }
    assert.equal(await evaluate('document.documentElement.scrollWidth'), width);
  }
  pass('empty results have a working clear-filter action and layouts fit desktop/mobile widths');

  await navigate('/roommate/' + unsafe.id);
  assert.equal(await evaluate(`document.querySelector('.detail-copy h1').textContent`), unsafeName);
  assert.equal(await evaluate(`document.querySelector('.detail-card img') === null && window.pwned === undefined`), true);
  assert.equal(await evaluate('document.documentElement.scrollWidth'), 360);
  await navigate('/roommate/999999');
  assert.equal(await evaluate(`document.querySelector('h1').textContent`), 'Profile unavailable');
  await api(`fetch('/auth/logout', {method:'POST', headers:{'Content-Type':'application/json',
    'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content}, body:'{}'})`);
  await cdp('Page.navigate', {url:base + '/find-roommates'});
  await wait(`location.pathname === '/login' && document.readyState === 'complete'`);
  assert.equal(await api(`fetch('/matches').then(r => r.status)`), 401);
  pass('detail escaping/404 states and logged-out matching protection work');

  const {runInterestChecks} = await import('./interests.mjs');
  await runInterestChecks({base, send, cdp, evaluate, wait, navigate, fill, pass, first, self, unsafe, gap});
  const {runNotificationChecks} = await import('./notifications.mjs');
  await runNotificationChecks({base, send, cdp, evaluate, pass, first, self, unsafe, gap});
  const {runPreferenceChecks} = await import('./preferences.mjs');
  await runPreferenceChecks({base, send, cdp, evaluate, pass, first, self, second});
  console.log(`${count} browser scenarios passed.`);
} finally {
  if (ws) ws.close();
  chrome.kill('SIGTERM');
  await sleep(500);
  await rm(directory, {recursive:true, force:true, maxRetries:3, retryDelay:100});
}
