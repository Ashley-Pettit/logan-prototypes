#!/usr/bin/env python3
"""Add (or replace) the "Steps to productionise" button and panel in a Logan AI prototype page.

Usage:
  python3 prod_panel.py <page.html> <plan.json> <out.html>

plan.json:
{
  "recommend": "azure" | "claude",
  "why": "One plain sentence on why that route suits this app.",
  "knowledge": ["What the tool needs to know, e.g. council Word docs ..."],
  "azure":  {"steps": ["..."], "setup": ["..."]},
  "claude": {"steps": ["..."], "setup": ["..."]}
}

The button sits in a slim bar at the top of the page, on the right. The panel has Azure, Claude and "Show me both" views.
Everything is scoped under #lpx-prod so it can't clash with the app's own styles.
"""
import json, re, sys

CSS = r"""
#lpx-prod-bar{display:flex;justify-content:flex-end;align-items:center;gap:10px;padding:calc(6px + env(safe-area-inset-top,0px)) 12px 6px;background:#F3F5F8;border-bottom:1px solid #DDE3EA;font:13px/1.3 Arial,Helvetica,sans-serif;color:#566273;position:relative;z-index:50}
@media (prefers-color-scheme:dark){#lpx-prod-bar{background:#121922;border-color:#2B3546;color:#A3AFBF}}
#lpx-prod-btn{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 14px;border-radius:999px;border:1px solid #003F75;background:#fff;color:#003F75;font:600 13px/1 Arial,Helvetica,sans-serif;cursor:pointer;white-space:nowrap}
#lpx-prod-btn:hover{background:#003F75;color:#fff}
@media (prefers-color-scheme:dark){#lpx-prod-btn{background:#18202C;color:#8EC1EC;border-color:#8EC1EC}#lpx-prod-btn:hover{background:#8EC1EC;color:#06233D}}
#lpx-prod-btn:focus-visible{outline:2px solid #1F6FBF;outline-offset:2px}
#lpx-prod-btn svg{width:16px;height:16px;flex:none}
@media (max-width:480px){#lpx-prod-bar .lpx-q{display:none}}
@media (pointer:coarse){#lpx-prod-btn{min-height:44px}}
#lpx-prod{--bg:#fff;--soft:#F3F5F8;--ink:#1B2430;--muted:#566273;--rule:#DDE3EA;--brand:#003F75;--on:#fff;--az:#0F6CBD;--cl:#B4532A;
  position:fixed;inset:0;z-index:2147483001;display:none;font:14px/1.5 Arial,Helvetica,sans-serif;color:var(--ink)}
@media (prefers-color-scheme:dark){#lpx-prod{--bg:#18202C;--soft:#212B3B;--ink:#E7ECF2;--muted:#A3AFBF;--rule:#2B3546;--brand:#8EC1EC;--on:#06233D;--az:#6CB1F0;--cl:#F0A47E}}
#lpx-prod.open{display:block}
#lpx-prod .lpx-scrim{position:absolute;inset:0;background:rgba(10,20,35,.45)}
#lpx-prod .lpx-panel{position:absolute;top:0;right:0;bottom:0;width:min(640px,100vw);background:var(--bg);box-shadow:-8px 0 30px rgba(0,0,0,.2);display:flex;flex-direction:column;outline:none}
#lpx-prod .lpx-panel.lpx-wide{width:min(1040px,100vw)}
#lpx-prod header{padding:calc(16px + env(safe-area-inset-top,0px)) 20px 12px;border-bottom:1px solid var(--rule)}
#lpx-prod .lpx-hrow{display:flex;justify-content:space-between;align-items:flex-start;gap:12px}
#lpx-prod h2{margin:0;font-size:19px;color:var(--brand)}
#lpx-prod .lpx-sub{margin:4px 0 0;color:var(--muted);font-size:13px}
#lpx-prod .lpx-x{flex:none;width:36px;height:36px;border-radius:8px;border:1px solid var(--rule);background:var(--bg);color:var(--ink);font-size:20px;line-height:1;cursor:pointer}
#lpx-prod .lpx-seg{display:inline-flex;gap:2px;margin-top:12px;padding:3px;border-radius:8px;background:var(--soft);flex-wrap:wrap}
#lpx-prod .lpx-seg button{min-height:34px;padding:0 14px;border:0;border-radius:6px;background:none;color:var(--muted);font:600 13px Arial,Helvetica,sans-serif;cursor:pointer}
#lpx-prod .lpx-seg button[aria-pressed="true"]{background:var(--bg);color:var(--brand);box-shadow:0 1px 2px rgba(0,0,0,.1),inset 0 0 0 1px var(--rule)}
#lpx-prod .lpx-rec{margin-top:10px;font-size:13px;color:var(--ink);background:var(--soft);border-radius:6px;padding:8px 10px}
#lpx-prod .lpx-rec b{color:var(--brand)}
#lpx-prod .lpx-body{flex:1;overflow:auto;padding:16px 20px calc(24px + env(safe-area-inset-bottom,0px))}
#lpx-prod .lpx-cols{display:grid;gap:16px;grid-template-columns:1fr}
#lpx-prod .lpx-wide .lpx-cols{grid-template-columns:1fr 1fr}
@media (max-width:760px){#lpx-prod .lpx-wide .lpx-cols{grid-template-columns:1fr}}
#lpx-prod section{border:1px solid var(--rule);border-radius:8px;padding:14px 16px;margin-bottom:12px;background:var(--bg)}
#lpx-prod h3{margin:0 0 8px;font-size:14px;display:flex;align-items:center;gap:8px}
#lpx-prod .lpx-tag{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;color:#fff}
#lpx-prod .lpx-tag.az{background:var(--az)}
#lpx-prod .lpx-tag.cl{background:var(--cl)}
#lpx-prod .lpx-tag.kn{background:#5B4237}
#lpx-prod ol,#lpx-prod ul{margin:0;padding-left:20px}
#lpx-prod li{margin:4px 0}
#lpx-prod .lpx-foot{color:var(--muted);font-size:12px;margin-top:4px}
#lpx-prod button:focus-visible{outline:2px solid #1F6FBF;outline-offset:2px}
@media (pointer:coarse){#lpx-prod .lpx-seg button,#lpx-prod .lpx-x{min-height:44px;min-width:44px}}
"""

JS = r"""
(function(){
  if (window.__lpxProd) return; window.__lpxProd = true;
  function boot(){
    var el = document.getElementById('lpx-prod-plan'); if (!el) return;
    var P = JSON.parse(el.textContent);
    function e(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
    function list(items, tag){return '<'+tag+'>'+(items||[]).map(function(x){return '<li>'+e(x)+'</li>';}).join('')+'</'+tag+'>';}
    var btn = document.createElement('button');
    btn.id = 'lpx-prod-btn'; btn.type = 'button'; btn.setAttribute('aria-haspopup','dialog');
    btn.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M3 13l4-4 2 2 4-5M10 6h3v3" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg><span>Steps to productionise</span>';
    var wrap = document.createElement('div'); wrap.id = 'lpx-prod';
    wrap.innerHTML = '<div class="lpx-scrim"></div><div class="lpx-panel" role="dialog" aria-modal="true" aria-labelledby="lpx-h" tabindex="-1">'+
      '<header><div class="lpx-hrow"><div><h2 id="lpx-h">Steps to productionise</h2><p class="lpx-sub">How this prototype could become a supported council tool.</p></div>'+
      '<button type="button" class="lpx-x" aria-label="Close">&times;</button></div>'+
      '<div class="lpx-seg" role="group" aria-label="Show steps for"><button type="button" data-v="azure">Azure</button><button type="button" data-v="claude">Claude</button><button type="button" data-v="both">Show me both</button></div>'+
      '<p class="lpx-rec"><b>Suggested route: '+(P.recommend==='claude'?'Claude':'Azure')+'.</b> '+e(P.why)+'</p></header>'+
      '<div class="lpx-body" id="lpx-body"></div></div>';
    var bar = document.createElement('div'); bar.id = 'lpx-prod-bar'; bar.innerHTML = '<span class="lpx-q">Thinking about going live?</span>'; bar.appendChild(btn);
    document.body.insertBefore(bar, document.body.firstChild); document.body.appendChild(wrap);
    var panel = wrap.querySelector('.lpx-panel'), body = wrap.querySelector('#lpx-body');
    var view = P.recommend === 'claude' ? 'claude' : 'azure';
    function sec(cls, label, title, inner){return '<section><h3><span class="lpx-tag '+cls+'">'+label+'</span>'+e(title)+'</h3>'+inner+'</section>';}
    function col(k){
      var az = k === 'azure', R = P[k] || {};
      return '<div>'+
        sec(az?'az':'cl', az?'Azure':'Claude', 'Steps to productionise ('+(az?'Azure':'Claude')+')', list(R.steps,'ol'))+
        sec(az?'az':'cl', az?'Azure':'Claude', 'What is needed to set it up in '+(az?'Azure':'Claude'), list(R.setup,'ul'))+
        '</div>';
    }
    function render(){
      wrap.querySelectorAll('.lpx-seg button').forEach(function(b){b.setAttribute('aria-pressed', String(b.dataset.v===view));});
      panel.classList.toggle('lpx-wide', view==='both');
      var kn = sec('kn','Knowledge','What knowledge does it need', list(P.knowledge,'ul'));
      body.innerHTML = (view==='both' ? '<div class="lpx-cols">'+col('azure')+col('claude')+'</div>' : col(view)) + kn +
        '<p class="lpx-foot">Draft for discussion. Systems, costs and approvals to be confirmed with ICT. Going live needs ICT-DA, CAB, PGG and Business System Owner approval.</p>';
    }
    var last = null;
    function open(){ last = document.activeElement; wrap.classList.add('open'); render(); panel.focus(); document.addEventListener('keydown', key); }
    function close(){ wrap.classList.remove('open'); document.removeEventListener('keydown', key); (last||btn).focus(); }
    function key(ev){
      if (ev.key === 'Escape') { close(); return; }
      if (ev.key !== 'Tab') return;
      var f = panel.querySelectorAll('button,a[href],[tabindex]:not([tabindex="-1"])'); if (!f.length) return;
      var a = f[0], z = f[f.length-1];
      if (ev.shiftKey && document.activeElement === a) { z.focus(); ev.preventDefault(); }
      else if (!ev.shiftKey && document.activeElement === z) { a.focus(); ev.preventDefault(); }
    }
    btn.addEventListener('click', open);
    wrap.querySelector('.lpx-x').addEventListener('click', close);
    wrap.querySelector('.lpx-scrim').addEventListener('click', close);
    wrap.querySelectorAll('.lpx-seg button').forEach(function(b){ b.addEventListener('click', function(){ view = b.dataset.v; render(); }); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
"""

START, END = "<!-- lpx-prod:start -->", "<!-- lpx-prod:end -->"


def build(plan):
    for k in ("recommend", "why", "knowledge", "azure", "claude"):
        assert k in plan, f"plan.{k} is missing"
    for k in ("azure", "claude"):
        assert plan[k].get("steps") and plan[k].get("setup"), f"plan.{k} needs steps and setup"
    data = json.dumps(plan, ensure_ascii=False).replace("</", "<\\/")
    return (f'{START}\n<style id="lpx-prod-css">{CSS}</style>\n'
            f'<script type="application/json" id="lpx-prod-plan">{data}</script>\n'
            f'<script>{JS}</script>\n{END}')


def inject(page, plan):
    block = build(plan)
    if START in page:
        s, e = page.index(START), page.index(END) + len(END)
        return page[:s] + block + page[e:]
    i = page.rfind("</body>")
    return page[:i] + block + "\n" + page[i:] if i > -1 else page + "\n" + block


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    page = open(sys.argv[1], encoding="utf-8").read()
    plan = json.load(open(sys.argv[2], encoding="utf-8"))
    open(sys.argv[3], "w", encoding="utf-8").write(inject(page, plan))
    print("ok", sys.argv[3])
