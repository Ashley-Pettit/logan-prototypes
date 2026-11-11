// End-to-end tests for My Desk.
// Run from the repo folder: node tests/e2e.js
// Serves the site locally, then runs every check on desktop and on several iPhone profiles.
// Note: Playwright's iPhone profiles use Chromium with iPhone screen size, touch and Safari's user agent.

const http = require('http');
const fs = require('fs');
const path = require('path');
const { chromium, devices } = require('playwright');

const ROOT = path.resolve(__dirname, '..');
const OUT = process.env.SHOTS || path.join(ROOT, 'tests', 'shots');
const TYPES = { '.html': 'text/html', '.svg': 'image/svg+xml', '.png': 'image/png', '.json': 'application/json', '.webmanifest': 'application/manifest+json' };

const PROFILES = [
  { name: 'Desktop', opts: { viewport: { width: 1280, height: 860 } }, phone: false },
  { name: 'iPhone SE', opts: devices['iPhone SE'], phone: true },
  { name: 'iPhone 15', opts: devices['iPhone 15'], phone: true },
  { name: 'iPhone 16 Pro Max', opts: devices['iPhone 16 Pro Max'], phone: true },
  { name: 'iPhone 15 landscape', opts: devices['iPhone 15 landscape'], phone: true }
];

let pass = 0, fail = 0;
const fails = [];
function check(profile, label, ok, info)
{
  if (ok) { pass++; }
  else { fail++; fails.push(profile + ' :: ' + label + (info ? ' (' + info + ')' : '')); }
}

// Serves the repo folder over http://127.0.0.1 so storage behaves like a real site.
function serve()
{
  return new Promise(function (resolve)
  {
    const srv = http.createServer(function (req, res)
    {
      let p = decodeURIComponent(req.url.split('?')[0].split('#')[0]);
      if (p.endsWith('/')) { p += 'index.html'; }
      const f = path.join(ROOT, p);
      if (!f.startsWith(ROOT) || !fs.existsSync(f)) { res.writeHead(404); res.end('nope'); return; }
      res.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' });
      fs.createReadStream(f).pipe(res);
    });
    srv.listen(0, '127.0.0.1', function () { resolve(srv); });
  });
}

async function noOverflow(page) { return page.evaluate(function () { return document.documentElement.scrollWidth <= window.innerWidth + 1; }); }
async function count(page, tab) { return parseInt(await page.textContent('#count-' + tab), 10); }
async function tap(page, sel, phone) { if (phone) { await page.tap(sel); } else { await page.click(sel); } }

async function run(base, profile, browser)
{
  const P = profile.name, phone = profile.phone;
  const ctx = await browser.newContext(Object.assign({ acceptDownloads: true }, profile.opts));
  const page = await ctx.newPage();
  const errors = [];
  page.on('pageerror', function (e) { errors.push(e.message); });
  page.on('console', function (m) { if (m.type() === 'error' && !/fonts\.(googleapis|gstatic)/.test(m.text())) { errors.push(m.text()); } });
  let dialogs = 0;
  page.on('dialog', function (d) { dialogs++; d.dismiss(); });

  // 1. First load
  await page.goto(base + '/');
  await page.waitForSelector('#panel-a .todo');
  check(P, 'title is My Desk', (await page.title()) === 'My Desk');
  check(P, 'examples banner shows', await page.isVisible('#examples'));
  check(P, 'work tab shows 3 open examples', (await count(page, 'a')) === 3, await count(page, 'a'));
  check(P, 'personal tab shows 3 open examples', (await count(page, 'b')) === 3);
  check(P, 'no sideways scroll on load', await noOverflow(page));

  if (phone)
  {
    // iOS zooms into any field under 16px when tapped.
    const small = await page.evaluate(function ()
    {
      return Array.from(document.querySelectorAll('input:not([type=checkbox]):not([type=radio]):not([type=file]), select'))
        .filter(function (i) { return i.offsetParent && parseFloat(getComputedStyle(i).fontSize) < 16; }).map(function (i) { return i.id; });
    });
    check(P, 'no field under 16px (no iOS zoom)', small.length === 0, small.join(','));
    // Tap targets: report anything under 28px tall that is visible.
    const tiny = await page.evaluate(function ()
    {
      return Array.from(document.querySelectorAll('button, a, input[type=checkbox], summary'))
        .filter(function (b) { const r = b.getBoundingClientRect(); const min = b.type === 'checkbox' ? 22 : 28; return b.offsetParent && r.height > 0 && r.height < min; })
        .map(function (b) { return (b.id || b.className || b.tagName) + ':' + Math.round(b.getBoundingClientRect().height); });
    });
    check(P, 'tap targets at least 28px', tiny.length === 0, tiny.slice(0, 6).join(', '));
    const vp = await page.evaluate(function () { return document.querySelector('meta[name=viewport]').content; });
    check(P, 'viewport covers the notch', /viewport-fit=cover/.test(vp));
    check(P, 'home screen icon set', (await page.$('link[rel=apple-touch-icon]')) !== null);
    const iconOk = await page.evaluate(async function () { const r = await fetch(document.querySelector('link[rel=apple-touch-icon]').href); return r.ok; });
    check(P, 'home screen icon loads', iconOk);
    await page.screenshot({ path: path.join(OUT, P.replace(/\s+/g, '-') + '-1-start.png') });
  }

  // 2. Add a to-do with a group and urgent flag
  await page.fill('#add-a', 'Write the board paper');
  await page.fill('#grp-a', 'Testing');
  await tap(page, '#urg-a', phone);
  await tap(page, '#panel-a form button.btn', phone);
  check(P, 'add to-do raises count to 4', (await count(page, 'a')) === 4);
  const newRow = page.locator('#panel-a .todo', { hasText: 'Write the board paper' });
  check(P, 'new group created', (await page.locator('#panel-a .ghead', { hasText: 'Testing' }).count()) === 1);
  check(P, 'urgent pill on new to-do', (await newRow.textContent()).includes('Urgent'));
  check(P, 'add box clears after adding', (await page.inputValue('#add-a')) === '');
  check(P, 'empty add is ignored', await (async function () { await tap(page, '#panel-a form button.btn', phone); return (await count(page, 'a')) === 4; })());

  // 3. Tick done, then untick
  const row = page.locator('#panel-a .todo', { hasText: 'Write the board paper' });
  await row.locator('input[type=checkbox]').click();
  check(P, 'ticking lowers count', (await count(page, 'a')) === 3);
  await tap(page, '#panel-a details.donebox summary', phone);
  await page.locator('#panel-a .donebox .todo', { hasText: 'Write the board paper' }).locator('input[type=checkbox]').click();
  check(P, 'unticking restores count', (await count(page, 'a')) === 4);

  // 4. Urgent toggle
  const flagRow = page.locator('#panel-a .todo', { hasText: 'Book a catch-up' });
  await flagRow.locator('button[aria-label^="Urgent"]').click();
  check(P, 'urgent toggle adds pill', (await page.locator('#panel-a .todo', { hasText: 'Book a catch-up' }).textContent()).includes('Urgent'));

  // 5. Two-tap remove, including the time-out
  const delBtn = page.locator('#panel-a .todo', { hasText: 'Tidy up the shared drive' }).locator('button.del');
  await delBtn.click();
  check(P, 'first tap asks to confirm', (await delBtn.textContent()) === 'Remove');
  await page.waitForTimeout(3200);
  check(P, 'confirm resets after 3 seconds', (await delBtn.textContent()) !== 'Remove');
  await delBtn.click(); await delBtn.click();
  check(P, 'second tap removes', (await page.locator('#panel-a .todo', { hasText: 'Tidy up the shared drive' }).count()) === 0);

  // 6. Clear done items
  if (!(await page.isVisible('#panel-a .donebox .todo'))) { await tap(page, '#panel-a details.donebox summary', phone); }
  await page.locator('#panel-a .donebox button', { hasText: 'Clear done items' }).click();
  check(P, 'clear done empties done list', (await page.locator('#panel-a .donebox').count()) === 0);

  // 7. Typed text is shown as text, never run as code
  await page.fill('#add-a', '<img src=x onerror=alert(1)> Sneaky');
  await tap(page, '#panel-a form button.btn', phone);
  check(P, 'HTML in a to-do shows as text', (await page.locator('#panel-a .todo', { hasText: '<img src=x' }).count()) === 1 && dialogs === 0);
  const longWord = 'x'.repeat(250);
  await page.fill('#add-a', longWord);
  await tap(page, '#panel-a form button.btn', phone);
  check(P, 'very long to-do wraps, no sideways scroll', await noOverflow(page));

  // 8. Links: validation, normalising, safety
  await tap(page, '#panel-a details.linkadd summary', phone);
  await page.locator('#panel-a .linkform button.btn').click();
  check(P, 'link with no name shows an error', (await page.locator('#panel-a .linkform .err').textContent()).includes('name'));
  await page.fill('#lt-a', 'Bad one'); await page.fill('#lu-a', 'javascript:alert(1)');
  await page.locator('#panel-a .linkform button.btn').click();
  check(P, 'javascript: link is refused', (await page.locator('#panel-a .linkform .err').textContent()).includes('address'));
  await page.fill('#lu-a', 'example.com/page');
  await page.fill('#lg-a', 'Test links');
  await page.locator('#panel-a .linkform button.btn').click();
  const newLink = page.locator('#panel-a .llist a', { hasText: 'Bad one' });
  check(P, 'link saved with https added', (await newLink.getAttribute('href')) === 'https://example.com/page');
  check(P, 'link opens in a new tab safely', (await newLink.getAttribute('target')) === '_blank' && /noopener/.test(await newLink.getAttribute('rel')));
  check(P, 'add-link form stays open for the next one', await page.isVisible('#lt-a'));

  // 9. Filter appears past 8 links and keeps focus while typing
  for (let i = 1; i <= 5; i++) { await page.fill('#lt-a', 'Extra ' + i); await page.fill('#lu-a', 'https://example.org/' + i); await page.locator('#panel-a .linkform button.btn').click(); }
  check(P, 'filter shows with more than 8 links', await page.isVisible('#filter-a'));
  await page.click('#filter-a');
  await page.keyboard.type('extra 3');
  check(P, 'filter narrows the list', (await page.locator('#panel-a .llist a').count()) === 1);
  check(P, 'filter keeps focus while typing', await page.evaluate(function () { return document.activeElement && document.activeElement.id === 'filter-a'; }));
  await page.fill('#filter-a', 'zzz'); await page.dispatchEvent('#filter-a', 'input');
  await page.locator('#panel-a button', { hasText: 'Clear filter' }).click();
  check(P, 'clear filter brings links back', (await page.locator('#panel-a .llist a').count()) > 8);

  // 10. Remove a link
  const lrow = page.locator('#panel-a .llist li', { hasText: 'Extra 5' });
  await lrow.locator('button.del').click(); await lrow.locator('button.del').click();
  check(P, 'link removed', (await page.locator('#panel-a .llist a', { hasText: 'Extra 5' }).count()) === 0);

  // 11. Clear examples keeps the person's own items
  await tap(page, '#clear-examples', phone);
  check(P, 'examples banner hides', !(await page.isVisible('#examples')));
  check(P, 'example to-dos gone', (await page.locator('.pill.ex').count()) === 0);
  check(P, 'own to-dos kept', (await page.locator('#panel-a .todo', { hasText: 'Write the board paper' }).count()) === 1);

  // 12. Tabs and the address
  await tap(page, '#tab-b', phone);
  check(P, 'second tab shows', await page.isVisible('#panel-b') && !(await page.isVisible('#panel-a')));
  check(P, 'address remembers tab', page.url().endsWith('#second'));
  await page.reload(); await page.waitForSelector('#panel-b');
  check(P, 'reload stays on second tab', await page.isVisible('#panel-b'));
  check(P, 'personal tab starts empty after clearing examples', (await count(page, 'b')) === 0 && (await page.textContent('#panel-b')).includes('Nothing here yet'));
  if (!phone)
  {
    await page.focus('#tab-b'); await page.keyboard.press('ArrowLeft');
    check(P, 'arrow keys switch tabs', await page.isVisible('#panel-a'));
  }
  else { await tap(page, '#tab-a', phone); }

  // 13. Settings: cancel does nothing, save applies and persists
  await tap(page, '#open-settings', phone);
  check(P, 'settings opens', await page.isVisible('#settings'));
  const box = await page.locator('#settings').boundingBox();
  const vh = await page.evaluate(function () { return window.innerHeight; });
  const vw = await page.evaluate(function () { return window.innerWidth; });
  check(P, 'settings fits the screen', box && box.y >= 0 && box.y + box.height <= vh + 1 && box.x >= 0 && box.x + box.width <= vw + 1, JSON.stringify(box));
  if (phone) { check(P, 'keyboard not forced open on settings', await page.evaluate(function () { return document.activeElement.id !== 's-name'; })); }
  await page.fill('#s-name', 'Nobody');
  await page.locator('#settings button', { hasText: 'Cancel' }).click();
  await page.waitForTimeout(250);
  check(P, 'cancel discards changes', (await page.title()) === 'My Desk');
  await tap(page, '#open-settings', phone);
  await page.fill('#s-name', 'Sam Lee');
  await page.fill('#s-tagline', 'Ops team');
  await page.fill('#s-taba', 'Job'); await page.fill('#s-tabb', 'Home');
  await page.locator('#s-colours label[title=Plum]').click();
  await page.locator('.seg label', { hasText: 'Dark' }).click();
  if (phone) { await page.screenshot({ path: path.join(OUT, P.replace(/\s+/g, '-') + '-2-settings.png') }); }
  // On a small phone the Save button sits in the sticky footer; make sure it's reachable.
  await page.locator('#s-save').scrollIntoViewIfNeeded();
  await tap(page, '#s-save', phone);
  await page.waitForFunction(function () { return !document.getElementById('settings').open; });
  await page.waitForFunction(function () { return document.title !== 'My Desk'; }, null, { timeout: 3000 }).catch(function () {});
  check(P, 'name sets the title', (await page.title()) === 'Sam Lee’s Desk');
  check(P, 'initials worked out', (await page.textContent('#mark')) === 'SL');
  check(P, 'tagline shows', (await page.textContent('#sub')).startsWith('Ops team'));
  check(P, 'tab names change', (await page.textContent('#tabname-a')) === 'Job' && (await page.textContent('#tabname-b')) === 'Home');
  check(P, 'dark theme applied', (await page.getAttribute('html', 'data-theme')) === 'dark');
  const mastBg = await page.evaluate(function () { return getComputedStyle(document.querySelector('.mast')).backgroundColor; });
  check(P, 'plum colour applied', mastBg === 'rgb(91, 42, 110)', mastBg);
  const bodyBg = await page.evaluate(function () { return getComputedStyle(document.body).backgroundColor; });
  check(P, 'dark background', bodyBg === 'rgb(14, 20, 27)', bodyBg);
  check(P, 'no sideways scroll in dark', await noOverflow(page));
  if (phone) { await page.screenshot({ path: path.join(OUT, P.replace(/\s+/g, '-') + '-3-dark.png') }); }
  await page.reload(); await page.waitForSelector('#panel-a');
  check(P, 'settings survive reload', (await page.title()) === 'Sam Lee’s Desk' && (await page.getAttribute('html', 'data-theme')) === 'dark');
  check(P, 'to-dos survive reload', (await page.locator('#panel-a .todo', { hasText: 'Write the board paper' }).count()) === 1);

  // 14. Backup out, delete everything, backup back in
  await tap(page, '#open-settings', phone);
  const [dl] = await Promise.all([page.waitForEvent('download'), page.click('#s-export')]);
  const backupPath = path.join(OUT, P.replace(/\s+/g, '-') + '-backup.json');
  await dl.saveAs(backupPath);
  const backup = JSON.parse(fs.readFileSync(backupPath, 'utf8'));
  check(P, 'backup file named and complete', /^my-desk-backup-\d{4}-\d{2}-\d{2}\.json$/.test(dl.suggestedFilename()) && backup.todos.some(function (t) { return t.title === 'Write the board paper'; }) && backup.settings.name === 'Sam Lee');

  const badPath = path.join(OUT, 'not-a-backup.json');
  fs.writeFileSync(badPath, '{"hello":1}');
  await page.setInputFiles('#s-file', badPath);
  await page.waitForSelector('#s-import-err:not([hidden])');
  check(P, 'wrong file shows a clear error', (await page.textContent('#s-import-err')).includes('isn\'t a My Desk backup'));

  await page.locator('#s-reset').scrollIntoViewIfNeeded();
  await tap(page, '#s-reset', phone);
  check(P, 'delete asks twice', (await page.textContent('#s-reset')).includes('Tap again'));
  await tap(page, '#s-reset', phone);
  check(P, 'delete empties everything', (await count(page, 'a')) === 0 && (await page.title()) === 'My Desk');

  // A backup with a sneaky link should load but drop the bad link.
  const tampered = JSON.parse(JSON.stringify(backup));
  tampered.links.push({ id: 'evil', tab: 'a', group: 'Bad', title: 'Evil', url: 'javascript:alert(1)' });
  const tamperedPath = path.join(OUT, 'tampered.json');
  fs.writeFileSync(tamperedPath, JSON.stringify(tampered));
  await tap(page, '#open-settings', phone);
  await page.setInputFiles('#s-file', tamperedPath);
  await page.waitForFunction(function () { return document.title === 'Sam Lee’s Desk'; });
  check(P, 'backup loads everything back', (await page.locator('#panel-a .todo', { hasText: 'Write the board paper' }).count()) === 1);
  check(P, 'bad link in a backup is dropped', (await page.locator('.llist a', { hasText: 'Evil' }).count()) === 0);
  check(P, 'settings closes after loading', !(await page.isVisible('#settings')));

  // 15. Anna's copy keeps a separate list
  await page.goto(base + '/anna/');
  await page.waitForSelector('#panel-a .todo');
  check(P, 'Anna title', (await page.title()) === 'Anna’s Desk');
  check(P, 'Anna tagline', (await page.textContent('#sub')).startsWith('AI Transformation Lead'));
  check(P, 'Anna list separate from generic', (await page.locator('.todo', { hasText: 'Write the board paper' }).count()) === 0 && (await page.locator('.todo', { hasText: 'Shortlist the top AI use cases' }).count()) === 1);
  const annaBg = await page.evaluate(function () { return getComputedStyle(document.querySelector('.mast')).backgroundColor; });
  check(P, 'Anna teal colour', annaBg === 'rgb(13, 92, 88)', annaBg);
  check(P, 'Anna home screen icon loads', await page.evaluate(async function () { const r = await fetch(document.querySelector('link[rel=apple-touch-icon]').href); return r.ok; }));
  check(P, 'Anna no sideways scroll', await noOverflow(page));
  if (phone) { await page.screenshot({ path: path.join(OUT, P.replace(/\s+/g, '-') + '-4-anna.png') }); }
  await page.goto(base + '/');
  await page.waitForSelector('#panel-a');
  check(P, 'generic list untouched by Anna', (await page.title()) === 'Sam Lee’s Desk');

  check(P, 'no script errors', errors.length === 0, errors.slice(0, 3).join(' | '));
  check(P, 'no pop-up dialogs triggered', dialogs === 0);
  await ctx.close();
}

// Storage blocked (old private browsing): the page warns but still works.
async function blockedStorage(base, browser)
{
  const ctx = await browser.newContext(devices['iPhone 15']);
  await ctx.addInitScript(function () { Storage.prototype.setItem = function () { throw new Error('QuotaExceededError'); }; });
  const page = await ctx.newPage();
  await page.goto(base + '/'); await page.waitForSelector('#panel-a .todo');
  check('iPhone 15 storage blocked', 'warning shows', await page.isVisible('#storewarn'));
  await page.fill('#add-a', 'Still works'); await page.tap('#panel-a form button.btn');
  check('iPhone 15 storage blocked', 'can still add for this visit', (await page.locator('.todo', { hasText: 'Still works' }).count()) === 1);
  await ctx.close();
}

// Two open tabs stay in step.
async function twoTabs(base, browser)
{
  const ctx = await browser.newContext();
  const a = await ctx.newPage(), b = await ctx.newPage();
  await a.goto(base + '/'); await b.goto(base + '/');
  await a.waitForSelector('#panel-a .todo'); await b.waitForSelector('#panel-a .todo');
  await a.fill('#add-a', 'From the other tab'); await a.click('#panel-a form button.btn');
  await b.waitForTimeout(400);
  check('Desktop two tabs', 'change shows in the other tab', (await b.locator('.todo', { hasText: 'From the other tab' }).count()) === 1);
  await ctx.close();
}

(async function ()
{
  fs.mkdirSync(OUT, { recursive: true });
  const srv = await serve();
  const base = 'http://127.0.0.1:' + srv.address().port;
  const browser = await chromium.launch();
  for (const p of PROFILES)
  {
    try { await run(base, p, browser); }
    catch (e) { fail++; fails.push(p.name + ' :: crashed: ' + e.message.split('\n')[0]); }
  }
  try { await blockedStorage(base, browser); } catch (e) { fail++; fails.push('storage blocked :: crashed: ' + e.message.split('\n')[0]); }
  try { await twoTabs(base, browser); } catch (e) { fail++; fails.push('two tabs :: crashed: ' + e.message.split('\n')[0]); }
  await browser.close(); srv.close();
  console.log('\nPassed ' + pass + ', failed ' + fail);
  fails.forEach(function (f) { console.log('  FAIL ' + f); });
  process.exit(fail ? 1 : 0);
})();
