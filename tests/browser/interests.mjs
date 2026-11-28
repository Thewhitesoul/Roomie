// Two real browser contexts keep separate cookie/session jars. No mock auth/data.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

export async function runInterestChecks({base, send, cdp, evaluate, wait, navigate, fill, pass, first, self, unsafe, gap}) {
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
    const until = async expression => {
      for (let i=0; i<100; i++) {
        try { if (await inspect(expression)) return; } catch { /* Navigation changes context. */ }
        await new Promise(resolve => setTimeout(resolve,100));
      }
      throw new Error(`Interest browser condition timed out: ${expression}`);
    };
    const page = {command, inspect, until};
    page.go = async path => {
      await command('Page.navigate',{url:base+path});
      await until(`location.pathname === ${JSON.stringify(path.split('?')[0])} && document.readyState === 'complete'`);
    };
    page.ready = async () => until(`document.querySelector('[data-interest-panel], [data-matches-center]')?.dataset.loaded === 'true'
      && document.querySelector('[data-interest-panel], [data-matches-center]').getAttribute('aria-busy') === 'false'
      && document.querySelector('[data-notifications]').getAttribute('aria-busy') === 'false'`);
    page.click = async selector => inspect(`document.querySelector(${JSON.stringify(selector)}).click()`);
    page.change = async (method, uid) => inspect(`(async () => {
      const token=(await (await fetch('/auth/csrf')).json()).csrf_token;
      const response=await fetch('/interest/${uid}',{method:${JSON.stringify(method)}, credentials:'same-origin',
        headers:{'Content-Type':'application/json','X-CSRF-Token':token},body:'{}'});
      return {status:response.status, data:await response.json()};
    })()`);
    page.list = kind => inspect(`fetch('/interest/${kind}', {cache:'no-store'}).then(r => r.json())`);
    page.login = async (username, destination) => {
      await page.go('/login?next='+encodeURIComponent(destination));
      await inspect(`(() => {for(const [name,value] of Object.entries({email:${JSON.stringify(username+'@washburn.edu')},password:'password123'})) {
        const input=document.querySelector('section [name="'+name+'"]'); input.value=value;
        input.dispatchEvent(new Event('input',{bubbles:true}));
      } document.querySelector('section [data-auth-form]').requestSubmit();})()`);
      await until(`location.pathname === ${JSON.stringify(destination)} && document.readyState === 'complete'`);
      await page.ready();
    };
    page.refresh = async () => {
      await page.ready();
      await page.click('[data-interest-refresh]');
      await page.ready();
    };
    return page;
  };
  const A=makePage(cdp,evaluate), B=makePage(peerCdp,peerEval);
  const sentCard = uid => `[data-connections-section="sent"] [data-user-id="${uid}"]`;
  const receivedCard = uid => `[data-connections-section="received"] article[data-user-id="${uid}"]`;
  const mutualCard = uid => `[data-connections-section="mutual"] article[data-user-id="${uid}"]`;
  const sendButton='[data-interest-action="send"]';
  const withdrawButton='[data-interest-action="withdraw"]';
  try {
    await A.login('matching_self', '/roommate/'+first.id);
    await B.login('matching_first', '/roommate/'+self.id);
    assert.equal(await A.inspect(`fetch('/auth/me').then(r=>r.json()).then(d=>d.user.username)`),'matching_self');
    assert.equal(await B.inspect(`fetch('/auth/me').then(r=>r.json()).then(d=>d.user.username)`),'matching_first');
    assert.notEqual(first.id,first.user_id);
    assert.equal(await A.inspect(`document.querySelector('[data-interest-panel]').dataset.actionUrl`),'/interest/'+first.user_id);
    pass('two isolated browser sessions authenticate as different real users and target user IDs');

    await A.inspect(`document.querySelector('${sendButton}').click();document.querySelector('${sendButton}').click();`);
    await A.until(`document.querySelector('[data-interest-panel]').dataset.interestState === 'sent' && document.querySelector('[data-interest-panel]').getAttribute('aria-busy') === 'false'`);
    assert.equal((await A.list('sent')).length,1);
    assert.equal(await A.inspect(`document.querySelector('${sendButton}').textContent`),'Interest sent');
    assert.equal(await A.inspect(`document.querySelector('[data-mutual-banner]').hidden`),true);
    assert.equal((await A.list('mutual')).length,0);
    pass('Show Interest persists one outgoing request despite a double click, without a false mutual banner');

    await A.go('/my-matches'); await A.ready();
    assert.equal(await A.inspect(`document.querySelector('${sentCard(first.user_id)} a').getAttribute('href')`), base+'/roommate/'+first.id);
    const person=(await A.list('sent'))[0];
    const iso=new Date(person.since.replace(' ','T')+'Z').toISOString();
    assert.equal(await A.inspect(`document.querySelector('${sentCard(first.user_id)} time').dateTime`),iso);
    await A.command('Page.navigate',{url:base+'/roommate/'+first.id}); await A.until(`location.pathname === '/roommate/${first.id}'`); await A.ready();
    assert.equal(await A.inspect(`document.querySelector('${sendButton}').textContent`),'Interest sent');
    pass('returning to a profile restores SQLite state; My Matches links use profile IDs and real timestamps');

    await B.go('/my-matches'); await B.ready();
    assert.equal(await B.inspect(`!!document.querySelector('${receivedCard(self.user_id)}')`),true);
    assert.equal((await B.list('mutual')).length,0);
    await B.click(receivedCard(self.user_id)+' '+sendButton);
    await B.until(`!!document.querySelector('${mutualCard(self.user_id)}') && document.querySelector('[data-matches-center]').getAttribute('aria-busy') === 'false'`);
    assert.equal(await B.inspect(`document.querySelector('[data-mutual-banner]').hidden`),false);
    await A.refresh();
    assert.equal(await A.inspect(`document.querySelector('[data-interest-panel]').dataset.mutual`),'true');
    assert.equal(await A.inspect(`document.querySelector('[data-mutual-banner] h2').textContent`),"It's a Match!");
    assert.equal((await A.list('mutual'))[0].user_id,first.user_id);
    pass('only the second user reciprocating creates the real mutual match in both sessions');

    await A.go('/my-matches'); await A.ready();
    for (const width of [1440,768,360]) {
      await A.command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<800});
      assert.equal(await A.inspect('document.documentElement.scrollWidth'),width);
      const shot=await A.command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(join(tmpdir(),`roomie-my-matches-${width}.png`),Buffer.from(shot.data,'base64'));
    }
    assert(!(await A.inspect(`document.querySelector('[data-matches-center]').textContent`)).includes('@washburn.edu'));
    await A.click(mutualCard(first.user_id)+' '+withdrawButton);
    await A.until(`!document.querySelector('${mutualCard(first.user_id)}') && document.querySelector('[data-matches-center]').getAttribute('aria-busy') === 'false'`);
    assert.equal((await A.list('sent')).length,0);
    assert.equal((await A.list('received')).length,1);
    assert.equal(await A.inspect(`!!document.querySelector('${receivedCard(first.user_id)} ${sendButton}')`),true);
    await B.refresh();
    assert.equal((await B.list('mutual')).length,0);
    assert.equal(await B.inspect(`document.querySelector('[data-mutual-banner]').hidden`),true);
    await B.click(sentCard(self.user_id)+' '+withdrawButton);
    await B.until(`!document.querySelector('${sentCard(self.user_id)}') && document.querySelector('[data-matches-center]').getAttribute('aria-busy') === 'false'`);
    pass('mutual withdrawal updates every list for both users, preserves the reverse interest, and fits mobile layouts');

    await A.go('/roommate/'+first.id); await A.ready();
    assert.equal((await A.change('POST',first.user_id)).status,201);
    await A.click(sendButton);
    await A.until(`document.querySelector('[data-interest-feedback]').textContent.includes('already sent') && document.querySelector('[data-interest-panel]').getAttribute('aria-busy') === 'false'`);
    assert.equal((await A.list('sent')).length,1);
    assert.equal((await A.change('DELETE',first.user_id)).status,200);
    await A.click(withdrawButton);
    await A.until(`document.querySelector('[data-interest-panel]').dataset.interestState === 'not-sent' && document.querySelector('[data-interest-panel]').getAttribute('aria-busy') === 'false'`);
    assert.equal((await A.list('sent')).length,0);
    pass('duplicate POST 409 and already-withdrawn DELETE 404 reconcile to authoritative state');

    await A.inspect(`window.savedInterestCsrf=document.querySelector('meta[name="csrf-token"]').content;document.querySelector('meta[name="csrf-token"]').content='invalid';`);
    await A.click(sendButton);
    await A.until(`document.querySelector('[data-interest-feedback]').textContent.includes('security token')`);
    assert.equal((await A.list('sent')).length,0);
    assert.equal(await A.inspect(`document.querySelector('${sendButton}').disabled`),true);
    await A.inspect(`document.querySelector('meta[name="csrf-token"]').content=window.savedInterestCsrf;`);
    await A.click('[data-interest-refresh]'); await A.ready();
    assert.equal(await A.inspect(`document.querySelector('${sendButton}').disabled`),false);
    assert.equal((await A.change('POST',999999)).status,404);
    assert.equal((await A.change('POST',self.user_id)).status,400);
    pass('browser mutations enforce CSRF and reject nonexistent/self targets without creating records');

    assert.equal((await A.change('POST',gap.id)).status,201);
    assert.equal((await A.change('POST',unsafe.user_id)).status,201);
    await A.go('/my-matches'); await A.ready();
    assert.equal(await A.inspect(`document.querySelector('${sentCard(gap.id)} h3').textContent`),'matching_gap');
    assert.equal(await A.inspect(`document.querySelector('${sentCard(gap.id)} a')`),null);
    assert.equal(await A.inspect(`document.querySelector('${sentCard(gap.id)} .connection-profile-missing').textContent`),'Profile not available yet.');
    assert.equal(await A.inspect(`document.querySelector('${sentCard(unsafe.user_id)} h3').textContent`),unsafe.name);
    assert.equal(await A.inspect(`document.querySelector('.connections-grid img') === null && window.pwned === undefined`),true);
    await A.click(sentCard(gap.id)+' '+withdrawButton);
    await A.until(`!document.querySelector('${sentCard(gap.id)}') && document.querySelector('[data-matches-center]').getAttribute('aria-busy') === 'false'`);
    await A.click(sentCard(unsafe.user_id)+' '+withdrawButton);
    await A.until(`!document.querySelector('${sentCard(unsafe.user_id)}') && document.querySelector('[data-matches-center]').getAttribute('aria-busy') === 'false'`);
    pass('profile-less users have honest fallbacks; untrusted names render as text and never expose private account fields');

    await A.command('Network.enable');
    await A.command('Network.setBlockedURLs',{urls:[base+'/interest/sent']});
    await A.go('/my-matches');
    await A.until(`document.querySelector('[data-interest-feedback]').textContent.includes('Unable to reach')`);
    assert.equal(await A.inspect(`document.querySelector('[data-mutual-banner]').hidden`),true);
    assert.equal(await A.inspect(`document.querySelectorAll('.connection-card').length`),0);
    await A.command('Network.setBlockedURLs',{urls:[]});
    await A.click('[data-interest-refresh]'); await A.ready();
    assert.equal(await A.inspect(`document.querySelector('[data-connections-section="mutual"] [data-section-state]').hidden`),false);
    pass('loading failures show errors instead of fabricated empty/mutual data, and Refresh recovers');

    await A.inspect(`fetch('/auth/logout',{method:'POST',headers:{'Content-Type':'application/json',
      'X-CSRF-Token':document.querySelector('meta[name="csrf-token"]').content},body:'{}'})`);
    await A.click('[data-interest-refresh]');
    await A.until(`!document.querySelector('[data-interest-login]').hidden`);
    assert.equal(await B.inspect(`fetch('/auth/me').then(r=>r.json()).then(d=>d.user.username)`),'matching_first');
    await A.command('Page.navigate',{url:base+'/my-matches'});
    await A.until(`location.pathname === '/login' && location.search === '?next=/my-matches'`);
    pass('session expiry clears private lists and redirects safely without affecting the other browser session');
  } finally {
    await send('Target.disposeBrowserContext',{browserContextId:context.browserContextId});
  }
}
