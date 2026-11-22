// Real forms, CSRF, SQLite, and two independent authenticated browser contexts.
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';

export async function runPreferenceChecks({base, send, cdp, evaluate, pass, first, self, second}) {
  const context = await send('Target.createBrowserContext', {disposeOnDetach:true});
  const target = await send('Target.createTarget', {url:'about:blank',browserContextId:context.browserContextId});
  const attached = await send('Target.attachToTarget', {targetId:target.targetId,flatten:true});
  const peerCdp = (method, params) => send(method, params, attached.sessionId);
  await peerCdp('Page.enable');
  await peerCdp('Runtime.enable');
  const peerEval = async expression => {
    const result = await peerCdp('Runtime.evaluate', {expression,awaitPromise:true,returnByValue:true});
    if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  const makePage = (command, inspect) => {
    const page = {command, inspect};
    page.until = async expression => {
      for (let i=0;i<100;i++) {
        try { if (await inspect(expression)) return; } catch { /* Navigation changes context. */ }
        await new Promise(resolve=>setTimeout(resolve,100));
      }
      throw new Error(`Preferences browser condition timed out: ${expression}`);
    };
    page.go = async path => {
      await command('Page.navigate',{url:base+path});
      await page.until(`location.pathname === ${JSON.stringify(path.split('?')[0])} && document.readyState === 'complete'`);
    };
    page.ready = () => page.until(`!!document.querySelector('[data-preferences-form]') && !document.querySelector('[data-preferences-form] [type="submit"]').disabled`);
    page.click = selector => inspect(`document.querySelector(${JSON.stringify(selector)}).click()`);
    page.fill = values => inspect(`(() => {for(const [name,value] of Object.entries(${JSON.stringify(values)})) {
      const el=document.querySelector('[data-preferences-form] [name="'+name+'"]');el.value=value;
      el.dispatchEvent(new Event('input',{bubbles:true}));}})()`);
    page.values = () => inspect(`Object.fromEntries([...document.querySelectorAll('[data-preferences-form] select, [data-preferences-form] input')].map(el=>[el.name,el.value]))`);
    page.submit = () => inspect(`document.querySelector('[data-preferences-form]').requestSubmit()`);
    page.saved = () => page.until(`location.pathname === '/preferences' && !!document.querySelector('[data-preferences-overview]') && document.readyState === 'complete'`);
    page.api = async (path, method='GET', data={}) => inspect(`(async () => {
      const options={method:${JSON.stringify(method)},credentials:'same-origin',cache:'no-store'};
      if(options.method!=='GET') {
        const token=(await(await fetch('/auth/csrf')).json()).csrf_token;
        options.headers={'Content-Type':'application/json','X-CSRF-Token':token};
        options.body=${JSON.stringify(typeof data === 'string' ? data : JSON.stringify(data))};
      }
      const r=await fetch(${JSON.stringify(path)},options);return {status:r.status,data:await r.json().catch(()=>null)};
    })()`);
    page.login = async username => {
      await page.go('/login?next=/preferences');
      await inspect(`(() => {for(const [name,value] of Object.entries({email:${JSON.stringify(username+'@washburn.edu')},password:'password123'})) {
        const el=document.querySelector('section [name="'+name+'"]');el.value=value;
        el.dispatchEvent(new Event('input',{bubbles:true}));
      }document.querySelector('section [data-auth-form]').requestSubmit();})()`);
      await page.saved();
    };
    page.edit = async () => {await page.go('/preferences/edit');await page.ready();};
    return page;
  };
  const A=makePage(cdp,evaluate), B=makePage(peerCdp,peerEval);
  const fields={cleanliness:'very_clean',sleep_schedule:'late',study_habits:'mixed',
    smoking_preference:'non_smoking',pet_preference:'pets_ok',budget:'950'};
  const dto={...fields,budget:950};
  const nulls=Object.fromEntries(Object.keys(fields).map(key=>[key,null]));
  try {
    await A.command('Emulation.setDeviceMetricsOverride',{width:1440,height:1000,deviceScaleFactor:1,mobile:false});
    await A.command('Page.navigate',{url:base+'/preferences/edit'});
    await A.until(`location.pathname === '/login' && location.search === '?next=/preferences' && document.readyState === 'complete'`);
    assert.equal((await A.api('/preferences/me')).status,401);
    assert.equal((await A.api('/preferences/me','PUT',dto)).status,401);
    pass('preferences overview/editor and API reject unauthenticated access through existing session/CSRF protections');

    await A.login('matching_first');
    assert.deepEqual((await A.api('/preferences/me')).data,{user_id:first.user_id,...nulls});
    assert.equal(await A.inspect(`document.querySelectorAll('.preferences-overview > .profile-content').length`),1);
    assert.equal(await A.inspect(`document.querySelectorAll('.preferences-overview a[href="/preferences/edit"]').length`),1);
    assert.equal(await A.inspect(`document.querySelector('[data-preferences-form]')`),null);
    assert((await A.inspect(`document.querySelector('.preference-options').textContent`)).includes('Relaxed'));
    await A.click('.preferences-overview a[href="/preferences/edit"]');await A.ready();
    assert.deepEqual(await A.values(),Object.fromEntries(Object.keys(fields).map(key=>[key,''])));
    pass('first visit shows real null preferences, available choices, one white card, and one Edit action');

    const originalProfile=(await A.api('/profiles/me')).data;
    const originalMatches=(await A.api('/matches')).data;
    const originalInterests=(await A.api('/interest/sent')).data;
    await A.fill(fields);await A.submit();await A.saved();
    assert.deepEqual((await A.api('/preferences/me')).data,{user_id:first.user_id,...dto});
    assert.equal(await A.inspect(`document.querySelector('[data-preference-value="cleanliness"]').textContent`),'Very clean');
    assert.equal(await A.inspect(`document.querySelector('[data-preference-value="budget"]').textContent`),'$950/month');
    assert((await A.inspect(`document.querySelector('#main').textContent`)).includes('Preferences saved.'));
    assert.deepEqual((await A.api('/profiles/me')).data,originalProfile);
    assert.deepEqual((await A.api('/matches')).data,originalMatches);
    assert.deepEqual((await A.api('/interest/sent')).data,originalInterests);
    pass('all six fields save through real PUT/CSRF and display saved values without changing profile budget, discovery, or interests');

    await A.go('/preferences');
    await A.edit();assert.deepEqual(await A.values(),fields);
    await A.fill({budget:'1050',sleep_schedule:'early'});
    await A.click('[data-preferences-form] a[href="/preferences"]');await A.saved();
    assert.deepEqual((await A.api('/preferences/me')).data,{user_id:first.user_id,...dto});
    pass('refresh restores SQLite data and Cancel discards edits without a write');

    for (const mode of ['overview','editor']) {
      if(mode==='editor') await A.edit();else await A.go('/preferences');
      for(const width of [1440,768,360]) {
        await A.command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<800});
        assert.equal(await A.inspect('document.documentElement.scrollWidth'),width);
        assert.equal(await A.inspect(`document.querySelectorAll('.preferences-overview > .profile-content').length`),1);
        const shot=await A.command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
        await writeFile(join(tmpdir(),`roomie-preferences-${mode}-${width}.png`),Buffer.from(shot.data,'base64'));
      }
    }
    pass('saved preferences and editor keep a single card and fit desktop/tablet/360px mobile layouts');

    await A.fill({...Object.fromEntries(Object.keys(fields).map(key=>[key,''])),budget:'0'});
    await A.submit();await A.saved();
    assert.deepEqual((await A.api('/preferences/me')).data,{user_id:first.user_id,...nulls,budget:0});
    assert.equal(await A.inspect(`document.querySelector('[data-preference-value="budget"]').textContent`),'$0/month');
    await A.edit();await A.fill({budget:''});await A.submit();await A.saved();
    assert.deepEqual((await A.api('/preferences/me')).data,{user_id:first.user_id,...nulls});
    pass('No preference choices and blank budgets store null, while a zero-dollar budget remains zero');

    await A.edit();await A.fill({budget:'9223372036854775807'});await A.submit();await A.saved();
    assert((await A.inspect(`fetch('/preferences/me',{cache:'no-store'}).then(r=>r.text())`)).includes('9223372036854775807'));
    assert.equal(await A.inspect(`document.querySelector('[data-preference-value="budget"]').textContent`),'$9223372036854775807/month');
    await A.edit();assert.equal((await A.values()).budget,'9223372036854775807');
    await A.fill(fields);await A.submit();await A.saved();
    pass('the full SQLite whole-dollar integer range saves and prefills exactly without JavaScript rounding');

    await A.edit();
    for(const value of ['-1','2.5','9223372036854775808']) {
      await A.fill({budget:value});await A.submit();
      assert.equal(await A.inspect(`document.querySelector('[name="budget"]').checkValidity()`),false);
      assert.equal((await A.api('/preferences/me')).data.budget,950);
    }
    for(const body of ['{"budget":true}','{"budget":"500"}','{"budget":1.5}','{"budget":9223372036854775808}']) {
      assert.equal((await A.api('/preferences/me','PUT',body)).status,400);
    }
    await A.fill({budget:'975'});
    await A.inspect(`(() => {const select=document.querySelector('[name="cleanliness"]');
      select.add(new Option('Invalid text','x'.repeat(101)));select.value='x'.repeat(101);})()`);
    await A.submit();
    await A.until(`document.querySelector('[data-preferences-form] .form-feedback').textContent.includes('100 characters')`);
    assert.equal((await A.values()).cleanliness.length,101);
    assert.equal((await A.api('/preferences/me')).data.budget,950);
    pass('invalid budgets are blocked and real API validation errors preserve edits and saved data');

    await A.fill(fields);
    await A.inspect(`document.querySelector('meta[name="csrf-token"]').content='invalid'`);
    await A.submit();
    await A.until(`document.querySelector('[data-preferences-form] .form-feedback').textContent.includes('security token')`);
    assert.deepEqual(await A.values(),fields);
    assert.equal((await A.api('/preferences/me')).data.budget,950);
    await A.inspect(`fetch('/auth/csrf').then(r=>r.json()).then(d=>{document.querySelector('meta[name="csrf-token"]').content=d.csrf_token;})`);
    pass('a rejected CSRF token leaves all preference values intact and shows the actual security error');

    await A.command('Network.enable');
    await A.command('Network.setBlockedURLs',{urls:[base+'/preferences/me']});
    await A.fill({budget:'975'});await A.submit();
    await A.until(`document.querySelector('[data-preferences-form] .form-feedback').textContent.includes('Unable to reach')`);
    assert.equal((await A.values()).budget,'975');
    await A.command('Network.setBlockedURLs',{urls:[]});
    assert.equal((await A.api('/preferences/me')).data.budget,950);
    await A.submit();await A.saved();
    assert.equal((await A.api('/preferences/me')).data.budget,975);
    pass('network failures keep unsaved edits and a successful retry returns to the saved overview');

    const custom='<img src=x onerror=window.preferencePwned=1>';
    assert.equal((await A.api('/preferences/me','PUT',{cleanliness:custom})).status,200);
    await A.go('/preferences');
    assert.equal(await A.inspect(`document.querySelector('[data-preference-value="cleanliness"]').textContent`),custom);
    assert.equal(await A.inspect(`document.querySelector('.preferences-overview img') === null && window.preferencePwned === undefined`),true);
    await A.edit();assert.equal((await A.values()).cleanliness,custom);
    await A.submit();await A.saved();
    assert.equal((await A.api('/preferences/me')).data.cleanliness,custom);
    await A.edit();await A.fill({...fields,budget:'975'});await A.submit();await A.saved();
    pass('existing free-text preference values remain prefilled, save unchanged, and render safely as text');

    await B.login('matching_self');
    assert.deepEqual((await B.api('/preferences/me')).data,{user_id:self.user_id,...nulls});
    await B.edit();await B.fill({cleanliness:'relaxed',budget:'300'});await B.submit();await B.saved();
    assert.equal((await A.api('/preferences/me')).data.budget,975);
    assert.equal((await B.api('/preferences/me')).data.budget,300);
    assert.equal((await A.api('/preferences/me?user_id='+self.user_id)).data.user_id,first.user_id);
    assert.deepEqual((await A.api('/profiles/me')).data,originalProfile);
    pass('two independent authenticated browser sessions save isolated preferences and never synchronize profile budgets');

    await B.go('/roommate/'+first.id);
    await B.until(`document.querySelector('[data-interest-panel]')?.dataset.loaded === 'true'`);
    assert.notEqual(first.id,first.user_id);
    const shared='/preferences/profile/'+first.id;
    assert.deepEqual((await B.api(shared)).data,{...dto,budget:975});
    const sharedValues = page => page.inspect(`Object.fromEntries([...document.querySelectorAll('[data-roommate-preference]')].map(el=>[el.dataset.roommatePreference,el.textContent]))`);
    assert.deepEqual(await sharedValues(B),{
      cleanliness:'Very clean',sleep_schedule:'Night owl',study_habits:'A mix of both',
      smoking_preference:'Non-smoking',pet_preference:'Pets are okay',budget:'$975/month',
    });
    assert.equal((await B.api('/preferences/me')).data.budget,300);
    assert.equal(await B.inspect(`document.querySelector('[data-roommate-preferences]').previousElementSibling.classList.contains('tags')`),true);
    assert.equal(await B.inspect(`document.querySelector('[data-roommate-preferences]').closest('.detail-card') !== null`),true);
    assert.equal(await B.inspect(`document.querySelector('[data-interest-panel]').dataset.userId`),String(first.user_id));
    assert.equal(await B.inspect(`document.querySelector('.detail-copy > .profile-budget').textContent`),'Budget: $600/month');
    assert.equal(await B.inspect(`document.querySelectorAll('[data-roommate-preferences] button, [data-roommate-preferences] input, [data-roommate-preferences] form').length`),0);
    assert(!(await B.inspect(`document.querySelector('.detail-card').textContent`)).includes('@washburn.edu'));
    pass('roommate profile shows only the target’s six saved lifestyle fields below Interests, with no viewer-budget fallback or edit controls');

    for(const width of [1440,768,360]) {
      await B.command('Emulation.setDeviceMetricsOverride',{width,height:1000,deviceScaleFactor:1,mobile:width<800});
      assert.equal(await B.inspect('document.documentElement.scrollWidth'),width);
      const shot=await B.command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});
      await writeFile(join(tmpdir(),`roomie-roommate-lifestyle-${width}.png`),Buffer.from(shot.data,'base64'));
    }
    pass('shared lifestyle settings remain inside the existing white profile container at desktop, tablet, and 360px widths');

    await B.go('/roommate/'+second.id);
    assert.deepEqual((await B.api('/preferences/profile/'+second.id)).data,nulls);
    assert.deepEqual(await sharedValues(B),Object.fromEntries(Object.keys(fields).map(key=>[key,'Not specified'])));
    pass('a roommate without saved preferences shows six Not specified values even when viewer and profile budgets exist');

    assert.equal((await B.api(shared,'PUT',{budget:1})).status,405);
    assert.equal((await B.api('/preferences/me','PUT',{user_id:first.user_id,budget:1})).status,400);
    assert.deepEqual((await B.api(shared+'?user_id='+self.user_id)).data,{...dto,budget:975});
    assert.equal((await B.api('/preferences/me')).data.budget,300);
    pass('the profile-ID sharing API exposes no ownership metadata and rejects writes or ownership spoofing');

    await A.edit();
    assert((await A.inspect(`document.querySelector('#preferences-visibility').textContent`)).includes('visible to other logged-in Roomie users'));
    await A.fill({sleep_schedule:'early',budget:'1100'});await A.submit();await A.saved();
    await B.go('/roommate/'+first.id);
    assert.equal((await sharedValues(B)).sleep_schedule,'Early sleeper');
    assert.equal((await sharedValues(B)).budget,'$1100/month');
    const hostile='<img src=x onerror=window.sharedPreferencePwned=1>';
    assert.equal((await A.api('/preferences/me','PUT',{cleanliness:hostile})).status,200);
    await B.go('/roommate/'+first.id);
    assert.equal((await sharedValues(B)).cleanliness,hostile);
    assert.equal(await B.inspect(`document.querySelector('[data-roommate-preferences] img') === null && window.sharedPreferencePwned === undefined`),true);
    await A.edit();await A.fill({...fields,budget:'975'});await A.submit();await A.saved();
    pass('the editor explains sharing; real saves update another session’s profile view and custom settings render as text');

    await A.api('/auth/logout','POST');await A.login('matching_first');
    assert.deepEqual((await A.api('/preferences/me')).data,{user_id:first.user_id,...dto,budget:975});
    await A.edit();assert.deepEqual(await A.values(),{...fields,budget:'975'});
    pass('logout/login persistence restores every saved preference and returns to the intended Preferences page');

    await A.fill({budget:'1000'});await A.api('/auth/logout','POST');
    await A.inspect(`fetch('/auth/csrf').then(r=>r.json()).then(d=>{document.querySelector('meta[name="csrf-token"]').content=d.csrf_token;})`);
    await A.submit();
    await A.until(`!document.querySelector('[data-preferences-login]').hidden`);
    assert.equal(await A.inspect(`document.querySelector('[data-preferences-form] [type="submit"]').disabled`),true);
    assert.equal((await A.api('/preferences/me')).status,401);
    assert.equal((await B.api('/preferences/me')).data.budget,300);
    assert.equal((await B.api('/auth/me')).data.user.username,'matching_self');
    pass('expired sessions cannot save or view preferences and do not affect the other authenticated browser');
    assert.equal((await A.api(shared)).status,401);
    assert.deepEqual((await B.api(shared)).data,{...dto,budget:975});
    pass('shared preferences require an authenticated session while another signed-in browser retains read-only access');
  } finally {
    await send('Target.disposeBrowserContext',{browserContextId:context.browserContextId});
  }
}
