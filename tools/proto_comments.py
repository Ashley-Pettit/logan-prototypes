#!/usr/bin/env python3
"""Comments for the AI builder, on each app in the pipeline's "AI prototypes" tab.

Each app row in the AI prototypes list has a Comment button; its comments show straight under the row
(open ones first, then closed ones marked Actioned or Not changed with what was done). People leave a comment for the AI builder (what to fix,
add or change). Comments are saved in the pipeline artifact's own database (collection "ai_comments"),
so they work in copies a (Polish) and b (Mock), which declare the db and user capabilities. Copies c and
d (password locked, GitHub) can't save, so they show the comments box with a link to copy b instead.

Each comment document: {app: "APP-31", text, by (viewer id or null), at (ISO time), status: "open" |
"actioned" | "declined", actionedAt, actionNote, actionedVersion}. The AI builder marks a comment "actioned"
with ArtifactData "update" once it has done what the comment asks, or "declined" with the reason in actionNote
when it can't (outside the guardrails, unclear, or not about the app). Both count as closed.

Usage (run from the repo root):
  python3 tools/proto_comments.py inject <page.html> <out.html> [--password PW]
      Adds (or replaces) the comments module in a pipeline page. Idempotent. Locked pages need --password.
  python3 tools/proto_comments.py summary <dir> [<dir> ...]
      Reads comment JSON files saved by ArtifactData "list" with out_dir (each <dir>/ai_comments/<id>.json,
      one dir per copy) and prints the open comments grouped by app, oldest first, as JSON:
      {"apps": [{"app": "APP-31", "oldest": "...", "comments": [{"id", "where", "at", "text"}]}], "open": N}
      "where" is the dir name you passed (use the copy name, e.g. polish or mock).
"""
import argparse, glob, json, os, sys

START, END = "<!-- lpx-cmt:start -->", "<!-- lpx-cmt:end -->"
MAIN = "https://claude.ai/artifact/6PgxpQSDdJs1HjPxfZ7LvQ#ai-prototypes"

BLOCK = r"""<!-- lpx-cmt:start -->
<style id="lpx-cmt-css">
#proto .lpx-cbtn{font:inherit;font-size:12px;font-weight:700;cursor:pointer;display:inline-flex;align-items:center;gap:5px;background:var(--card,#fff);color:#003F75;border:1px solid #9fb6cc}
#proto .lpx-cbtn svg{width:12px;height:12px;flex:none}
#proto .lpx-cbtn:hover{background:#e3edf6}
#proto .lpx-cbtn.has{background:#fbe9e1;color:#8a3a17;border-color:#f0c4b0}
#proto .lpx-cbtn:focus-visible{outline:2px solid #1F6FBF;outline-offset:2px}
#proto .lpx-cstrip{margin:-2px 4px 10px 80px;display:grid;gap:6px}
#proto .lpx-cstrip:empty{display:none}
#proto .lpx-cstrip ul{list-style:none;margin:0;padding:0;display:grid;gap:6px}
#proto .lpx-cstrip li{border:1px solid var(--rule,#DDE3EA);border-left:4px solid #B4532A;border-radius:8px;padding:7px 10px;display:grid;gap:3px;background:var(--card,#fff);font-size:14px}
#proto .lpx-cstrip li.done{border-left-color:#1d6b35}
#proto .lpx-cstrip .lpx-cm{display:flex;flex-wrap:wrap;gap:4px 8px;align-items:center;font-size:12px;color:var(--muted,#566273)}
#proto .lpx-cstrip .lpx-cm b{color:var(--ink,#1B2430)}
#proto .lpx-cstrip .lpx-cm button{margin-left:auto}
#proto .lpx-cstrip .lpx-ct{margin:0;white-space:pre-wrap;overflow-wrap:anywhere}
#proto .lpx-cstrip .lpx-ca{margin:0;font-size:13px;color:#1d6b35}
#proto .lpx-cstrip .lpx-cnote{margin:0;font-size:13px;color:var(--muted,#566273)}
#proto .lpx-cpill{font-size:11px;font-weight:700;padding:1px 8px;border-radius:999px;background:#fbe9e1;color:#8a3a17}
#proto li.done .lpx-cpill{background:#e6f4ea;color:#1d6b35}
#proto .lpx-cstrip form{display:grid;gap:6px;border:1px solid var(--rule,#DDE3EA);border-radius:8px;padding:10px;background:var(--soft,#F3F5F8)}
#proto .lpx-cstrip label{font-size:13px;font-weight:600}
#proto .lpx-cstrip textarea{font:inherit;font-size:15px;width:100%;min-height:60px;resize:vertical;padding:8px 10px;border:1px solid var(--rule,#DDE3EA);border-radius:8px;background:var(--card,#fff);color:var(--ink,#1B2430)}
#proto .lpx-cstrip .lpx-crow{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
#proto .lpx-cstrip .lpx-crow>span:last-child{display:flex;gap:8px}
#proto .lpx-cstrip .lpx-cmsg{font-size:13px;color:var(--muted,#566273)}
#proto .lpx-cstrip .lpx-cmsg.bad{color:#b42318;font-weight:600}
#proto .lpx-cstrip button{font:inherit;font-size:13px;font-weight:600;min-height:32px;padding:0 14px;border-radius:999px;cursor:pointer;border:1px solid #003F75;background:#003F75;color:#fff}
#proto .lpx-cstrip button.lpx-cg{background:transparent;color:#003F75}
#proto .lpx-cstrip button.lpx-clink{border:0;background:none;color:#003F75;padding:0;min-height:0;text-decoration:underline;justify-self:start}
#proto .lpx-cstrip button:disabled{opacity:.55;cursor:default}
#proto .lpx-cstrip button:focus-visible,#proto .lpx-cstrip textarea:focus-visible{outline:2px solid #1F6FBF;outline-offset:2px}
#proto .lpx-cstrip .lpx-cm button{min-height:28px;padding:0 10px;font-size:12px}
@media (max-width:820px){#proto .lpx-cstrip{margin-left:4px}}
@media (max-width:600px){#proto details.prow>summary{grid-template-columns:minmax(0,1fr)!important}#proto details.prow>summary .pchips{display:flex;flex-wrap:wrap;justify-content:flex-start;gap:6px}}
@media (prefers-color-scheme:dark){#proto .lpx-cpill,#proto .lpx-cbtn.has{background:#3a2117;color:#f3b79a;border-color:#6b3a24}#proto .lpx-cbtn{color:#8EC1EC;border-color:#465368}#proto li.done .lpx-cpill{background:#14301d;color:#86d19c}#proto .lpx-cstrip .lpx-ca{color:#86d19c}#proto .lpx-cstrip button{background:#8EC1EC;border-color:#8EC1EC;color:#06233D}#proto .lpx-cstrip button.lpx-cg,#proto .lpx-cstrip button.lpx-clink{background:transparent;color:#8EC1EC}}
@media (pointer:coarse){#proto .lpx-cstrip button,#proto .lpx-cbtn{min-height:44px}}
</style>
<script>
/* Comments for the AI builder: a Comment button on every app row in the AI prototypes tab, with the
   app's comments shown straight under the row. Saved in this page's database. */
(function ()
{
  if (window.__lpxCmt) { return; } window.__lpxCmt = true;
  var COL = 'ai_comments', MAIN = '__MAIN__';
  var DB = null, USER = null, ME = null, CANWRITE = false, CANEDIT = false, STATE = 'wait', NAMES = {};
  var BY = {}, DRAFT = {}, MSG = {}, OPEN = {}, SHOWDONE = {};
  var ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M2.5 3.5h11v7h-6l-3 2.5v-2.5h-2z" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  function e(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function day(iso) { var d = new Date(iso); return isNaN(d) ? '' : d.toLocaleDateString('en-AU', { day: 'numeric', month: 'short', year: 'numeric' }); }
  function isClosed(c) { return c.status === 'actioned' || c.status === 'declined'; }
  function openCount(app) { return (BY[app] || []).filter(function (c) { return !isClosed(c); }).length; }

  function itemHtml(c)
  {
    var done = isClosed(c), dec = c.status === 'declined';
    var who = c.by && c.by === ME ? 'You' : (c.by && NAMES[c.by]) || 'Someone';
    return '<li class="' + (done ? 'done' : '') + '"><div class="lpx-cm"><b>' + e(who) + '</b><span>' + e(day(c.at)) + '</span><span class="lpx-cpill">' + (dec ? 'Not changed' : done ? 'Actioned' : 'Open') + '</span>' +
      (CANEDIT ? '<button type="button" class="lpx-cg" data-cmark="' + e(c.id) + '">' + (done ? 'Reopen' : 'Mark actioned') + '</button>' : '') + '</div>' +
      '<p class="lpx-ct">' + e(c.text) + '</p>' +
      (done ? '<p class="lpx-ca">' + (dec ? 'Not changed' : 'Actioned') + (c.actionedVersion ? ' in v' + e(c.actionedVersion) : '') + (c.actionedAt ? ' on ' + e(day(c.actionedAt)) : '') + (c.actionNote ? ': ' + e(c.actionNote) : '') + '</p>' : '') + '</li>';
  }
  // Every comment shows under the row: open ones first, then closed ones marked Actioned (or Not changed)
  // with what was done, so a comment never seems to disappear once the AI builder deals with it.
  function listHtml(app)
  {
    var L = BY[app] || [], open = L.filter(function (c) { return !isClosed(c); }), done = L.filter(isClosed);
    var all = open.concat(done);
    return all.length ? '<ul>' + all.map(itemHtml).join('') + '</ul>' : '';
  }
  function formHtml(app)
  {
    if (STATE === 'wait') { return '<p class="lpx-cnote">Loading comments…</p>'; }
    if (STATE === 'off') { return '<p class="lpx-cnote">Comments are kept in the AI &amp; Automation Pipeline on claude.ai. <a href="' + MAIN + '" target="_blank" rel="noopener">Open it to read or add comments</a>.</p>'; }
    if (STATE === 'err') { return '<p class="lpx-cnote">Comments couldn\'t be loaded just now. Reload the page to try again.</p>'; }
    if (!CANWRITE) { return '<p class="lpx-cnote">You can read comments here but not add them. Ask Ash for edit access to this page to comment.</p>'; }
    var id = 'lpx-c-' + app;
    return '<form data-capp="' + e(app) + '" novalidate><label for="' + e(id) + '">Comment for the AI builder on ' + e(app) + '</label>' +
      '<textarea id="' + e(id) + '" maxlength="1000" placeholder="What should change? For example: add a way to print the result, or the wording is too formal."></textarea>' +
      '<div class="lpx-crow"><span class="lpx-cmsg" role="status">The AI builder works on open comments first and marks each one actioned when done.</span><span><button type="button" class="lpx-cg" data-cclose="' + e(app) + '">Cancel</button><button type="submit">Add comment</button></span></div></form>';
  }
  // Adds the Comment button to one app row and keeps the strip under it up to date (typing isn't lost).
  function decorate(row)
  {
    var pid = row.querySelector('.pid'), chips = row.querySelector('summary .pchips');
    if (!pid || !chips) { return; }
    var app = pid.textContent.trim(), n = openCount(app);
    var btn = chips.querySelector('.lpx-cbtn');
    if (!btn) { btn = document.createElement('button'); btn.type = 'button'; btn.className = 'pchip lpx-cbtn'; btn.setAttribute('data-ctoggle', app); chips.insertBefore(btn, chips.firstChild); }
    btn.classList.toggle('has', n > 0);
    btn.innerHTML = ICON + (n ? n + (n === 1 ? ' comment' : ' comments') : 'Comment');
    btn.setAttribute('aria-expanded', OPEN[app] ? 'true' : 'false');
    btn.setAttribute('aria-label', (n ? n + ' open ' + (n === 1 ? 'comment' : 'comments') + '. ' : '') + (OPEN[app] ? 'Close the comment box for ' : 'Add a comment for the AI builder on ') + app);
    var strip = row.nextElementSibling;
    if (!strip || !strip.classList.contains('lpx-cstrip') || strip.getAttribute('data-capp') !== app)
    {
      strip = document.createElement('div'); strip.className = 'lpx-cstrip'; strip.setAttribute('data-capp', app);
      strip.innerHTML = '<div class="lpx-cl"></div><div class="lpx-cf"></div>';
      row.parentNode.insertBefore(strip, row.nextSibling);
    }
    var cl = strip.querySelector('.lpx-cl'), cf = strip.querySelector('.lpx-cf'), lh = listHtml(app);
    if (cl.innerHTML !== lh) { cl.innerHTML = lh; }
    var want = OPEN[app] ? STATE + CANWRITE : '';
    if (cf.getAttribute('data-state') !== want)
    {
      cf.innerHTML = OPEN[app] ? formHtml(app) : ''; cf.setAttribute('data-state', want);
      var ta = cf.querySelector('textarea'); if (ta && DRAFT[app]) { ta.value = DRAFT[app]; }
    }
    var m = cf.querySelector('.lpx-cmsg'); if (m && MSG[app]) { m.textContent = MSG[app].t; m.className = 'lpx-cmsg' + (MSG[app].bad ? ' bad' : ''); }
    if (!cl.innerHTML && !cf.innerHTML) { strip.hidden = true; } else { strip.hidden = false; }
  }
  function decorateAll()
  {
    var L = document.getElementById('p-list'); if (!L) { return; }
    // Drop strips left behind by a re-render, then decorate each row.
    L.querySelectorAll('.lpx-cstrip').forEach(function (s) { var p = s.previousElementSibling; if (!p || !p.matches('details.prow')) { s.remove(); } });
    L.querySelectorAll('details.prow').forEach(decorate);
  }

  function names()
  {
    var ids = [];
    Object.keys(BY).forEach(function (k) { BY[k].forEach(function (c) { if (c.by && !(c.by in NAMES) && ids.indexOf(c.by) < 0) { ids.push(c.by); } }); });
    if (!USER || !USER.profiles || !ids.length) { return; }
    USER.profiles(ids).then(function (ps) { ids.forEach(function (i) { NAMES[i] = (ps && ps[i] && ps[i].name) || ''; }); decorateAll(); }, function () {});
  }
  function connect()
  {
    var tries = 0;
    (function wait()
    {
      if (window.claude && typeof window.claude.use === 'function') { start(); return; }
      if (++tries > 30) { STATE = 'off'; decorateAll(); return; }
      setTimeout(wait, 100);
    })();
  }
  function start()
  {
    Promise.all(['db', 'user'].map(function (n) { return window.claude.use(n).catch(function () { return null; }); })).then(function (r)
    {
      DB = r[0]; USER = r[1];
      if (!DB) { STATE = 'off'; decorateAll(); return; }
      var checks = USER ? [USER.id().catch(function () { return null; }), USER.can('data.write').catch(function () { return null; }), USER.canEdit().catch(function () { return false; })] : [null, null, false];
      Promise.all(checks).then(function (u)
      {
        ME = u[0]; CANWRITE = u[1] !== false; CANEDIT = u[2] === true;
        var timer = setTimeout(function () { if (STATE === 'wait') { STATE = 'err'; decorateAll(); } }, 10000);
        DB.collection(COL).onSnapshot(function (snap)
        {
          clearTimeout(timer); STATE = 'ok'; BY = {};
          snap.docs.forEach(function (d)
          {
            var c = d.data() || {};
            if (typeof c.app !== 'string' || typeof c.text !== 'string') { return; }
            (BY[c.app] = BY[c.app] || []).push({ id: d.id, app: c.app, text: c.text.slice(0, 1000), by: typeof c.by === 'string' ? c.by : null, at: c.at, status: c.status === 'actioned' || c.status === 'declined' ? c.status : 'open', actionedAt: c.actionedAt, actionNote: typeof c.actionNote === 'string' ? c.actionNote.slice(0, 600) : '', actionedVersion: c.actionedVersion });
          });
          Object.keys(BY).forEach(function (k) { BY[k].sort(function (a, b) { return String(b.at).localeCompare(String(a.at)); }); });
          decorateAll(); names();
        }, function () { clearTimeout(timer); STATE = 'err'; decorateAll(); });
      });
    });
  }

  document.addEventListener('input', function (ev)
  {
    var f = ev.target.closest && ev.target.closest('.lpx-cstrip form');
    if (f) { DRAFT[f.getAttribute('data-capp')] = ev.target.value; }
  });
  document.addEventListener('submit', function (ev)
  {
    var f = ev.target.closest && ev.target.closest('.lpx-cstrip form'); if (!f) { return; }
    ev.preventDefault();
    var app = f.getAttribute('data-capp'), ta = f.querySelector('textarea'), btn = f.querySelector('button'), msg = f.querySelector('.lpx-cmsg');
    var text = ta.value.replace(/\s+$/, '').replace(/^\s+/, '');
    if (!text) { msg.textContent = 'Type a comment first.'; msg.className = 'lpx-cmsg bad'; ta.focus(); return; }
    btn.disabled = true; msg.textContent = 'Saving…'; msg.className = 'lpx-cmsg';
    DB.collection(COL).add({ app: app, text: text.slice(0, 1000), by: ME || null, at: new Date().toISOString(), status: 'open' }).then(function ()
    {
      DRAFT[app] = ''; ta.value = ''; MSG[app] = { t: 'Comment added. The AI builder will pick it up on its next run.' };
      msg.textContent = MSG[app].t; msg.className = 'lpx-cmsg'; btn.disabled = false;
    }, function ()
    {
      MSG[app] = { t: 'Your comment wasn\'t saved. You may not have edit access to this page.', bad: true };
      msg.textContent = MSG[app].t; msg.className = 'lpx-cmsg bad'; btn.disabled = false;
    });
  });
  document.addEventListener('click', function (ev)
  {
    var t = ev.target.closest && ev.target.closest('[data-ctoggle],[data-cclose],[data-cdone]');
    if (t)
    {
      // The Comment button sits inside the row's summary: stop it opening or closing the row.
      ev.preventDefault(); ev.stopPropagation();
      var ap = t.getAttribute('data-ctoggle') || t.getAttribute('data-cclose') || t.getAttribute('data-cdone');
      if (t.hasAttribute('data-cdone')) { SHOWDONE[ap] = !SHOWDONE[ap]; decorateAll(); return; }
      OPEN[ap] = t.hasAttribute('data-ctoggle') ? !OPEN[ap] : false;
      if (!OPEN[ap]) { MSG[ap] = null; }
      decorateAll();
      var s = document.querySelector('.lpx-cstrip[data-capp="' + ap + '"]');
      if (OPEN[ap] && s) { var ta = s.querySelector('textarea'); if (ta) { ta.focus(); } else { s.scrollIntoView({ block: 'nearest' }); } }
      else { var bt = document.querySelector('.lpx-cbtn[data-ctoggle="' + ap + '"]'); if (bt) { bt.focus(); } }
      return;
    }
    var b = ev.target.closest && ev.target.closest('[data-cmark]'); if (!b || !DB) { return; }
    var id = b.getAttribute('data-cmark'), c = null;
    Object.keys(BY).forEach(function (k) { BY[k].forEach(function (x) { if (x.id === id) { c = x; } }); });
    if (!c) { return; }
    b.disabled = true;
    var upd = isClosed(c) ? { status: 'open' } : { status: 'actioned', actionedAt: new Date().toISOString(), actionNote: 'Marked actioned by an editor.' };
    DB.collection(COL).doc(id).update(upd).catch(function () { b.disabled = false; });
  });

  document.addEventListener('keydown', function (ev)
  {
    if (ev.key !== 'Escape') { return; }
    var f = ev.target.closest && ev.target.closest('.lpx-cstrip form'); if (!f) { return; }
    var ap = f.getAttribute('data-capp'); OPEN[ap] = false; MSG[ap] = null; decorateAll();
    var bt = document.querySelector('.lpx-cbtn[data-ctoggle="' + ap + '"]'); if (bt) { bt.focus(); }
  });
  function boot()
  {
    var L = document.getElementById('p-list'); if (!L) { return; }
    new MutationObserver(function () { decorateAll(); }).observe(L, { childList: true });
    decorateAll(); connect();
  }
  if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', boot); } else { boot(); }
})();
</script>
<!-- lpx-cmt:end -->"""


def inject(page):
    """Adds the module just before </body> (or replaces an earlier copy)."""
    block = BLOCK.replace("__MAIN__", MAIN)
    if START in page:
        a = page.index(START)
        b = page.index(END, a) + len(END)
        return page[:a] + block + page[b:]
    i = page.rfind("</body>")
    return page[:i] + block + "\n" + page[i:] if i > -1 else page + block


def cmd_inject(a):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import proto_list as P
    html = open(a.page, encoding="utf-8").read()
    plain, m = (None, None)
    if P.LOCK.search(html):
        if not a.password:
            sys.exit("This page is locked: pass --password")
        plain, m = P.unlock(html, a.password)
    page = plain if plain is not None else html
    if 'id="p-list"' not in page:
        sys.exit("No AI prototypes list (#p-list) in this page")
    new = inject(page)
    if plain is not None:
        new = P.lock(html, m, new, a.password)
    open(a.out, "w", encoding="utf-8").write(new)
    print("ok", a.out, len(new))


def cmd_summary(a):
    by = {}
    total = 0
    for d in a.dirs:
        where = os.path.basename(os.path.normpath(d))
        for f in sorted(glob.glob(os.path.join(d, "**", "*.json"), recursive=True)):
            try:
                doc = json.load(open(f, encoding="utf-8"))
            except Exception:
                continue
            c = doc.get("data", doc) if isinstance(doc, dict) else {}
            if not isinstance(c, dict) or c.get("status") in ("actioned", "declined"):
                continue
            if not isinstance(c.get("app"), str) or not isinstance(c.get("text"), str):
                continue
            cid = doc.get("id") or os.path.splitext(os.path.basename(f))[0]
            by.setdefault(c["app"], []).append({"id": cid, "where": where, "at": c.get("at", ""), "text": c["text"][:1000]})
            total += 1
    apps = []
    for app, cs in by.items():
        cs.sort(key=lambda x: str(x["at"]))
        apps.append({"app": app, "oldest": cs[0]["at"], "comments": cs})
    apps.sort(key=lambda x: str(x["oldest"]))
    print(json.dumps({"open": total, "apps": apps}, indent=1, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("inject"); i.add_argument("page"); i.add_argument("out"); i.add_argument("--password")
    s = sub.add_parser("summary"); s.add_argument("dirs", nargs="+")
    a = ap.parse_args()
    {"inject": cmd_inject, "summary": cmd_summary}[a.cmd](a)


if __name__ == "__main__":
    main()
