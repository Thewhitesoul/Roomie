// Real SQLite-backed notifications in independent Chrome cookie jars.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

export async function runNotificationChecks({base, send, cdp, evaluate, pass, first, self, unsafe, gap}) {
  const context = await send('Target.createBrowserContext', {disposeOnDetach:true});
  const target = await send('Target.createTarget', {url:'about:blank', browserContextId:context.browserContextId});
  const attached = await send('Target.attachToTarget', {targetId:target.targetId, flatten:true});
  const peerCdp = (method, params) => send(method, params, attached.sessionId);
  await peerCdp('Page.enable');
  await peerCdp('Runtime.enable');
  await peerCdp('Emulation.setFocusEmulationEnabled', {enabled:true});
  const peerEval = async expression => {
    const result = await peerCdp('Runtime.evaluate', {expression, awaitPromise:true, returnByValue:true});
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const makePage = (command, inspect) => {
    const page = {command, inspect};
    page.until = async (expression, attempts=100) => {
      for (let i=0; i<attempts; i++) {
        try { if (await inspect(expression)) return; } catch { /* Navigation replaces context. */ }
        await new Promise(resolve => setTimeout(resolve,100));
      }
      throw new Error(`Notification browser condition timed out: ${expression}`);
    };
    page.go = async path => {
      await command('Page.navigate',{url:base+path});
      await page.until(`location.pathname === ${JSON.stringify(path)} && document.readyState === 'complete'`);
    };
    page.ready = () => page.until(`document.querySelector('[data-notifications]')?.dataset.loaded === 'true'
      && document.querySelector('[data-notifications]').getAttribute('aria-busy') === 'false'`);
    page.click = selector => inspect(`document.querySelector(${JSON.stringify(selector)}).click()`);
    page.refresh = async () => {
      await page.until(`!document.querySelector('[data-notification-refresh]').disabled`);
      await page.click('[data-notification-refresh]');
      await page.ready();
    };
    page.api = async (path, method, body={}) => inspect(`(async () => {
      const token=(await (await fetch('/auth/csrf')).json()).csrf_token;
      const response=await fetch(${JSON.stringify(path)}, {method:${JSON.stringify(method)}, credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:JSON.stringify(${JSON.stringify(body)})});
      return {status:response.status,data:await response.json()};
    })()`);
    page.login = async username => {
      await page.go('/login');
      await inspect(`(() => { for(const [name,value] of Object.entries({email:${JSON.stringify(username+'@washburn.edu')},password:'password123'})) {
        const input=document.querySelector('section [name="'+name+'"]');input.value=value;
        input.dispatchEvent(new Event('input',{bubbles:true}));
      } document.querySelector('section [data-auth-form]').requestSubmit();})()`);
      await page.until(`location.pathname === '/profile' && document.readyState === 'complete'`);
      await page.ready();
    };
    page.counts = () => inspect(`(() => {const n=document.querySelector('[data-notifications]');
      return [Number(n.dataset.pendingCount),Number(n.dataset.mutualCount)];})()`);
    return page;
  };
  const A=makePage(cdp,evaluate), B=makePage(peerCdp,peerEval);
  const key = async value => {
    const code = value === ' ' ? 'Space' : value;
    await A.command('Input.dispatchKeyEvent',{type:'keyDown',key:value,code});
    await A.command('Input.dispatchKeyEvent',{type:'keyUp',key:value,code});
  };
  const interestReady = page => page.until(`document.querySelector('[data-interest-panel], [data-matches-center]')?.dataset.loaded === 'true'
    && document.querySelector('[data-interest-panel], [data-matches-center]').getAttribute('aria-busy') === 'false'`);
  const pendingPerson = uid => `[data-notification-pending] [data-notification-user="${uid}"]`;
  try {
    await A.login('matching_self');
    await B.login('matching_first');
    assert.deepEqual(await A.counts(),[0,0]);
    assert.deepEqual(await B.counts(),[0,0]);
    assert.equal(await A.inspect(`document.querySelector('[data-notification-badge]').hidden && document.querySelector('[data-match-announcement]').hidden`),true);
    assert.equal(await A.inspect(`document.querySelector('[data-notification-mutual]').textContent`),'No matches yet');
    assert.equal(await A.inspect(`document.querySelector('[data-notification-feedback]').textContent`),'');
    assert.equal(await A.inspect(`document.querySelector('#notification-panel > .text-link').getAttribute('href')`),'/my-matches');
    assert.equal(await A.inspect(`document.querySelectorAll('.profile-content').length`),1);
    assert.equal(await A.inspect(`document.querySelectorAll('.profile-overview a[href="/profile/edit"]').length`),1);
    pass('authenticated notifications start empty in separate sessions and preserve the single-card profile');

    assert.equal(await A.inspect('document.hidden'),false);
    await A.inspect(`window.auditNotificationFocusChanges=0;
      window.addEventListener('focus',()=>{window.auditNotificationFocusChanges++;});
      document.addEventListener('visibilitychange',()=>{window.auditNotificationFocusChanges++;});`);
    await B.go('/roommate/'+self.id); await interestReady(B);
    await B.click('[data-interest-action="send"]');
    await B.until(`document.querySelector('[data-interest-panel]').dataset.interestState === 'sent'`);
    await B.go('/profile'); await B.ready();
    // Exercise the real 60-second visible-page interval, not a synthetic event.
    await A.until(`document.querySelector('[data-notifications]').dataset.pendingCount === '1'`,700);
    await A.ready();
    assert.equal(await A.inspect('window.auditNotificationFocusChanges'),0);
    pass('the real visible-page polling interval receives incoming interest without focus or manual refresh');
    assert.deepEqual(await A.counts(),[1,0]);
    assert.deepEqual(await B.counts(),[0,0]);
    assert.equal(await A.inspect(`document.querySelector('[data-notification-badge]').textContent`),'1');
    assert.equal(await A.inspect(`document.querySelector('${pendingPerson(first.user_id)} a').getAttribute('href')`),base+'/roommate/'+first.id);
    assert.equal(await A.inspect(`document.querySelector('${pendingPerson(first.user_id)} .notification-name').textContent`),first.name);
    assert.equal(await A.inspect(`document.querySelector('${pendingPerson(first.user_id)} .notification-label').textContent`),'Interested in you');
    assert.equal(await A.inspect(`document.querySelector('[data-match-announcement]').hidden`),true);
    pass('one-way interest notifies the recipient on their own profile with a real profile-ID link and pending count');

    await A.inspect(`document.querySelector('.notification-toggle').focus()`);
    await key(' ');
    assert.equal(await A.inspect(`document.querySelector('.notification-toggle').getAttribute('aria-expanded')`),'true');
    await key('ArrowDown');
    assert.equal(await A.inspect(`document.activeElement.hasAttribute('data-notification-refresh')`),true);
    await key('Tab');
    assert.equal(await A.inspect(`document.activeElement.closest('[data-notification-pending]') !== null`),true);
    await key('Escape');
    assert.equal(await A.inspect(`document.querySelector('#notification-panel').hidden && document.activeElement.classList.contains('notification-toggle')`),true);
    await key('Enter');
    await A.click('.profile-page-heading h1');
    assert.equal(await A.inspect(`document.querySelector('#notification-panel').hidden`),true);
    pass('notification disclosure supports Space, Enter, Tab, arrow keys, Escape with focus restoration, and outside click');

    for (const width of [1440,900,768,360]) {
      await A.command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<800});
      await A.click('.notification-toggle');
      assert.equal(await A.inspect('document.documentElement.scrollWidth'),width);
      assert.equal(await A.inspect(`(() => {const r=document.querySelector('#notification-panel').getBoundingClientRect();return r.left>=0 && r.right<=innerWidth;})()`),true);
      assert.equal(await A.inspect(`getComputedStyle(document.querySelector('#notification-panel')).backgroundColor`),'rgb(253, 253, 254)');
      assert.equal(await A.inspect(`getComputedStyle(document.querySelector('#notification-panel')).backdropFilter`),'none');
      const shot=await A.command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(join(tmpdir(),`roomie-notifications-${width}.png`),Buffer.from(shot.data,'base64'));
      await A.click('.notification-toggle');
    }
    pass('pending-interest panel and shared navigation fit desktop, tablet, and 360px mobile widths');

    await A.go('/my-matches'); await interestReady(A); await A.ready();
    await A.click(`[data-connections-section="received"] [data-user-id="${first.user_id}"] [data-interest-action="send"]`);
    await A.until(`document.querySelector('[data-notifications]').dataset.mutualCount === '1'
      && document.querySelector('[data-notifications]').getAttribute('aria-busy') === 'false'`);
    assert.deepEqual(await A.counts(),[0,1]);
    assert.equal(await A.inspect(`document.querySelector('[data-notification-badge]').hidden`),true);
    assert.equal(await A.inspect(`document.querySelector('[data-mutual-banner]').hidden`),false);
    await B.inspect(`window.dispatchEvent(new Event('focus'))`); await B.ready();
    await B.until(`document.querySelector('[data-notifications]').dataset.mutualCount === '1'`);
    assert.deepEqual(await B.counts(),[0,1]);
    assert.equal(await B.inspect('location.pathname'),'/profile');
    assert.equal(await B.inspect(`document.querySelector('[data-match-announcement] h2').textContent`),"It's a Match!");
    assert.equal(await B.inspect(`document.querySelector('[data-match-announcement]').hidden`),false);
    pass('reciprocating updates local notifications immediately and announces a true match on the other user’s own profile');

    await B.go('/'); await B.ready();
    assert.equal(await B.inspect(`document.querySelector('[data-match-announcement]').hidden`),false);
    assert.equal(await B.inspect(`document.querySelector('[data-match-announcement] a').getAttribute('href')`),'/my-matches');
    await B.go('/my-matches'); await interestReady(B); await B.ready();
    assert.equal(await B.inspect(`document.querySelectorAll('[data-connections-section="mutual"] article').length`),1);
    assert.equal(await B.inspect(`document.querySelector('[data-notification-mutual] [data-notification-user="${self.user_id}"]').textContent`),self.name);
    assert.equal(await B.inspect(`document.querySelectorAll('[data-notification-mutual] a, [data-notification-mutual] button').length`),0);
    assert(!(await B.inspect(`document.querySelector('[data-notifications]').textContent`)).includes('@washburn.edu'));
    pass('returning to the homepage restores a truthful match announcement and My Matches keeps the mutual card');

    await A.click(`[data-connections-section="mutual"] [data-user-id="${first.user_id}"] [data-interest-action="withdraw"]`);
    await A.until(`document.querySelector('[data-notifications]').dataset.pendingCount === '1'
      && document.querySelector('[data-notifications]').dataset.mutualCount === '0'`);
    assert.equal(await A.inspect(`document.querySelector('[data-mutual-banner]').hidden`),true);
    await B.refresh();
    assert.deepEqual(await B.counts(),[0,0]);
    assert.equal(await B.inspect(`document.querySelector('[data-mutual-banner]').hidden`),true);
    assert.equal(await B.inspect(`document.querySelectorAll('[data-connections-section="mutual"] article').length`),0);
    await B.go('/roommate/'+self.id); await interestReady(B);
    await B.click('[data-interest-action="withdraw"]');
    await B.until(`document.querySelector('[data-interest-panel]').dataset.interestState === 'not-sent'`);
    await A.refresh();
    assert.deepEqual(await A.counts(),[0,0]);
    pass('withdrawal removes mutual announcements in both sessions and counts only the remaining unreciprocated interest');
    await A.go('/profile'); await A.ready();

    // API sessions remain real even for accounts whose profile setup is incomplete.
    for (const username of ['matching_gap','matching_untrusted']) {
      assert.equal((await B.api('/auth/login','POST',{email:username+'@washburn.edu',password:'password123'})).status,200);
      assert.equal((await B.api('/interest/'+self.user_id,'POST')).status,201);
    }
    await A.refresh();
    assert.deepEqual(await A.counts(),[2,0]);
    assert.equal(await A.inspect(`document.querySelector('${pendingPerson(gap.id)} a')`),null);
    assert.equal(await A.inspect(`document.querySelector('${pendingPerson(gap.id)} small:not(.notification-label)').textContent`),'Profile not available yet.');
    assert.equal(await A.inspect(`document.querySelector('${pendingPerson(unsafe.user_id)} .notification-name').textContent`),unsafe.name);
    assert.equal(await A.inspect(`document.querySelector('#notification-panel img') === null && window.pwned === undefined`),true);
    pass('multiple incoming interests are counted; missing profiles and hostile names render safely without invented links');

    await A.command('Network.enable');
    await A.command('Network.setBlockedURLs',{urls:[base+'/interest/received']});
    await A.click('[data-notification-refresh]');
    await A.until(`document.querySelector('[data-notification-feedback]').textContent.includes('Unable to check')`);
    assert.equal(await A.inspect(`document.querySelector('[data-notifications]').dataset.loaded`),'false');
    assert.equal(await A.inspect(`document.querySelector('[data-notifications]').dataset.pendingCount`),undefined);
    assert.equal(await A.inspect(`document.querySelector('[data-notification-badge]').hidden && document.querySelector('[data-match-announcement]').hidden`),true);
    assert.equal(await A.inspect(`document.querySelectorAll('[data-notification-user]').length`),0);
    await A.command('Network.setBlockedURLs',{urls:[]});
    await A.refresh();
    assert.deepEqual(await A.counts(),[2,0]);
    pass('API failures clear stale notifications instead of claiming zero; Refresh restores confirmed counts');

    await A.api('/auth/logout','POST');
    await A.click('[data-notification-refresh]');
    await A.until(`!document.querySelector('[data-notification-login]').hidden`);
    assert.equal(await A.inspect(`document.querySelectorAll('[data-notification-user]').length`),0);
    assert.equal(await A.inspect(`document.querySelector('[data-notification-badge]').hidden && document.querySelector('[data-match-announcement]').hidden`),true);
    await B.go('/'); await B.ready();
    assert.deepEqual(await B.counts(),[0,0]);
    assert.equal(await B.inspect(`fetch('/auth/me').then(r=>r.json()).then(d=>d.user.username)`),'matching_untrusted');
    await A.go('/');
    assert.equal(await A.inspect(`document.querySelector('[data-notifications]')`),null);
    assert.equal(await A.inspect(`fetch('/interest/received').then(r=>r.status)`),401);
    pass('expired sessions clear all notification data; another authenticated account never sees the recipient’s private list');
  } finally {
    await send('Target.disposeBrowserContext',{browserContextId:context.browserContextId});
  }
}
