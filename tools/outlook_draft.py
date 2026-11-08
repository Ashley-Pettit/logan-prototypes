#!/usr/bin/env python3
"""Add "Draft in Outlook" buttons to a Logan AI prototype page.

Next to every button whose label starts with "Copy", the page gets a "Draft in Outlook" link.
Clicking it runs the Copy button (so the full text is also on the clipboard), catches the text,
and opens a new Outlook on the web email with the subject and text filled in. Nothing is sent:
the person checks the email in Outlook and presses Send. No connector or setup needed; it uses
whichever Microsoft 365 account is signed in to Outlook in the browser.

Usage: python3 outlook_draft.py <page.html> <out.html>      (replaces the block if already there)
"""
import sys

START, END = "<!-- lpx-outlook:start -->", "<!-- lpx-outlook:end -->"

BLOCK = r"""<!-- lpx-outlook:start -->
<style id="lpx-ol-css">
a.lpx-ol{display:inline-flex;align-items:center;gap:6px;text-decoration:none;cursor:pointer;white-space:nowrap}
a.lpx-ol svg{width:14px;height:14px;flex:none}
a.lpx-ol:focus-visible{outline:2px solid #1F6FBF;outline-offset:2px}
a.lpx-ol.lpx-ol-plain{min-height:32px;padding:0 12px;border-radius:6px;border:1px solid #0F6CBD;color:#0F6CBD;background:#fff;font:600 13px Arial,Helvetica,sans-serif}
a.lpx-ol.lpx-ol-plain:hover{background:#0F6CBD;color:#fff}
#lpx-ol-toast{position:fixed;left:50%;bottom:calc(20px + env(safe-area-inset-bottom,0px));transform:translateX(-50%);z-index:2147483002;max-width:min(520px,92vw);background:#1B2430;color:#fff;font:14px/1.4 Arial,Helvetica,sans-serif;padding:10px 14px;border-radius:8px;box-shadow:0 6px 20px rgba(0,0,0,.25);display:none}
@media (pointer:coarse){a.lpx-ol{min-height:44px}}
</style>
<script>
(function(){
  if (window.__lpxOutlook) return; window.__lpxOutlook = true;
  var MAX = 1600; // characters of body that fit safely in the Outlook link
  var BASE = 'https://outlook.office.com/mail/deeplink/compose';
  var ICON = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="1.5" y="3.5" width="13" height="9" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M2 4.5l6 4.5 6-4.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  function toast(msg){
    var t = document.getElementById('lpx-ol-toast');
    if (!t){ t = document.createElement('div'); t.id = 'lpx-ol-toast'; t.setAttribute('role','status'); document.body.appendChild(t); }
    t.textContent = msg; t.style.display = 'block';
    clearTimeout(t._h); t._h = setTimeout(function(){ t.style.display = 'none'; }, 6000);
  }
  function appName(){
    var t = (document.title || '').split(/\s[|\u2013-]\s/)[0].trim();
    if (t) return t;
    var h = document.querySelector('h1'); return h ? (h.firstChild && h.firstChild.textContent || h.textContent).trim() : 'Prototype';
  }
  function context(btn){
    var el = btn;
    for (var i = 0; i < 8 && el; i++){
      el = el.parentElement; if (!el) break;
      var hs = el.querySelectorAll('h2,h3,h4'), pick = null;
      for (var j = 0; j < hs.length; j++){
        if (hs[j].compareDocumentPosition(btn) & Node.DOCUMENT_POSITION_FOLLOWING) pick = hs[j];
      }
      if (pick){
        var t = pick.textContent.replace(/\s+/g,' ').trim();
        if (t && t.length <= 60) return t;
      }
    }
    return '';
  }
  function capture(btn){
    var got = null, clip = navigator.clipboard, real = clip && clip.writeText;
    if (clip && real){
      try { clip.writeText = function(t){ got = String(t); return real.call(clip, t).catch(function(){}); }; } catch(e){}
    }
    try { btn.click(); } catch(e){}
    if (clip && real){ try { clip.writeText = real; } catch(e){} }
    return got;
  }
  function build(btn, a){
    var text = capture(btn), ctx = context(btn), name = appName();
    var subject = ctx && ctx.toLowerCase() !== name.toLowerCase() ? name + ': ' + ctx : name;
    var body = '';
    if (text){
      body = text.length > MAX ? text.slice(0, MAX) + '\n\n[The full text is on your clipboard. Select everything above and paste with Ctrl+V.]' : text;
      toast(text.length > MAX ? 'Opening Outlook. The text was long, so the full version is on your clipboard too.' : 'Opening a new email in Outlook. Check it, add who it goes to, then press Send.');
    } else {
      toast('Opening a new email in Outlook. Paste the text in with Ctrl+V.');
    }
    a.href = BASE + '?subject=' + encodeURIComponent(subject) + (body ? '&body=' + encodeURIComponent(body) : '');
  }
  function enhance(){
    var btns = document.querySelectorAll('button');
    for (var i = 0; i < btns.length; i++){
      var b = btns[i];
      if (b.dataset.lpxOl || b.closest('#lpx-prod') || b.id === 'lpx-prod-btn') continue;
      var label = (b.textContent || '').replace(/\s+/g,' ').trim();
      if (!/^Copy\b/i.test(label) || /^Copying/i.test(label)) continue;
      b.dataset.lpxOl = '1';
      var a = document.createElement('a');
      a.href = BASE; a.target = '_blank'; a.rel = 'noopener';
      a.className = (b.className ? b.className + ' ' : '') + 'lpx-ol' + (b.className ? '' : ' lpx-ol-plain');
      a.innerHTML = ICON + '<span>Draft in Outlook</span>';
      a.title = 'Opens a new email in Outlook with this text. Nothing is sent until you press Send.';
      a.setAttribute('aria-label', 'Draft in Outlook: ' + label.replace(/^Copy\s*/i,'') );
      (function(btn, link){ link.addEventListener('click', function(){ build(btn, link); }); })(b, a);
      b.insertAdjacentElement('afterend', a);
    }
  }
  function boot(){
    enhance();
    var pending = false;
    new MutationObserver(function(){ if (pending) return; pending = true; requestAnimationFrame(function(){ pending = false; enhance(); }); })
      .observe(document.body, {childList: true, subtree: true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
</script>
<!-- lpx-outlook:end -->"""


def inject(page):
    if START in page:
        s, e = page.index(START), page.index(END) + len(END)
        return page[:s] + BLOCK + page[e:]
    i = page.rfind("</body>")
    return page[:i] + BLOCK + "\n" + page[i:] if i > -1 else page + "\n" + BLOCK


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    open(sys.argv[2], "w", encoding="utf-8").write(inject(open(sys.argv[1], encoding="utf-8").read()))
    print("ok", sys.argv[2])
