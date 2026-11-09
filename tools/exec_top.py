#!/usr/bin/env python3
"""Executive page top for the AI & Automation Pipeline (Polish and Mock copies).

Adds, at the top of the Executive tab:
  1. "How this works": the request process (from the page's own STEPS) and how data gets into the app.
  2. A row of stage cards with counts (click one to see those requests on Opportunities).
  3. The payoff and feasibility scatter and the Stage 2 AI readiness panel, moved here from the
     Opportunities "Map" view (the Map view is removed).
Also makes "Import Halo export" redact personal details (email addresses, phone numbers, street
addresses, long reference numbers; the requester's name is kept) and replace the built-in sample
requests once a real export has been imported.

Usage: python3 tools/exec_top.py <page.html> <out.html> [--password PW]
Idempotent: a page that already has it is left as it is (exit message "already").
"""
import argparse, os, re, sys

MARK = 'id="x-how"'

HOW = r"""
  <details class="card xhow" id="x-how" open>
    <summary><span>How this works</span><span class="xhow-t" aria-hidden="true"></span></summary>
    <div class="xhow-b">
      <section aria-labelledby="xp-h"><h4 id="xp-h">The process</h4><p class="note">Every idea staff raise goes through the same stages. A person makes each decision; the app scores and sorts to help.</p><ol class="xflow" id="x-proc"></ol></section>
      <section aria-labelledby="xd2-h"><h4 id="xd2-h">How data gets into the app</h4><ol class="xflow xdata">
        <li><b>Idea raised</b><span>Staff fill in the "Request AI Automation or Enhancement" form in the IT Service Portal (HaloITSM).</span></li>
        <li><b>Exported from Halo</b><span>The Master Report and the workflow history report are exported from Halo as CSV or Excel.</span></li>
        <li><b>Data redacted (person's name allowed)</b><span>On import, email addresses, phone numbers, street addresses and long reference numbers are stripped from the ticket text. The requester's name is kept so the team knows who to talk to.</span></li>
        <li><b>Idea created</b><span>"Import Halo export" (Opportunities, Import and export) turns each new ticket into a request and refreshes the status and dates of ones already here. A real import replaces the sample requests.</span></li>
        <li><b>Scored automatically</b><span>Each request gets a payoff and feasibility score, the seven Stage 2 AI readiness gates, the simplest fix and a duplicate check.</span></li>
        <li><b>People decide</b><span>A BA or coach reviews each request and moves it through the stages above. Decisions save to this page for everyone.</span></li>
        <li><b>Prototyped</b><span>Requests that are a good fit for AI go on the AI prototypes list, where the AI builder makes a rapid prototype. Comments on each app shape its next update.</span></li>
      </ol></section>
    </div>
  </details>
  <div class="xsteps" id="x-steps" role="group" aria-label="Requests by stage"></div>
  <div class="grid xmap">
    <section class="card c7" aria-labelledby="map-h"><h3 id="map-h">Payoff and feasibility of every open request <span class="xhint">· click a dot</span></h3><div class="scat" id="scat"></div><div class="legend" id="scat-lg"></div></section>
    <section class="card c5" aria-labelledby="rt-h"><h3 id="rt-h">Stage 2 AI readiness <span class="xhint">· click to filter</span></h3><div class="xready" id="tiles"></div><h3 class="h3gap">What's holding requests back</h3><div class="bars" id="b-gates"></div><p class="note" id="conf-note"></p><p class="note" id="dup-note"></p></section>
  </div>
"""

CSS = r"""<style id="xtop-css">
#exec .xhow{margin-bottom:12px;padding:0}
#exec .xhow>summary{list-style:none;cursor:pointer;display:flex;justify-content:space-between;align-items:center;gap:8px;padding:14px 18px;font-weight:600;font-size:16px;border-radius:inherit}
#exec .xhow>summary::-webkit-details-marker{display:none}
#exec .xhow>summary:focus-visible{outline:2px solid var(--accent,#1F6FBF);outline-offset:2px}
#exec .xhow .xhow-t::after{content:"Hide";font-size:13px;font-weight:500;color:var(--muted)}
#exec .xhow:not([open]) .xhow-t::after{content:"Show"}
#exec .xhow-b{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:20px;padding:0 18px 16px}
#exec .xhow-b h4{margin:0 0 4px;font-size:14px}
#exec .xhow-b .note{margin:0 0 8px}
#exec .xflow{list-style:none;margin:0;padding:0;counter-reset:xf;display:grid;gap:6px}
#exec .xflow li{counter-increment:xf;display:grid;grid-template-columns:26px minmax(0,1fr);column-gap:10px;font-size:14px;line-height:1.4;position:relative}
#exec .xflow li::before{content:counter(xf);grid-row:1/3;width:24px;height:24px;border-radius:50%;background:var(--xc,#003F75);color:#fff;font-size:12px;font-weight:700;display:grid;place-items:center}
#exec .xflow li b{font-weight:600}
#exec .xflow li span{color:var(--muted)}
#exec .xflow.xdata li::before{background:#5B4237}
#exec .xflow.xdata li:nth-child(3)::before{background:#C6246B}
#exec .xsteps{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin-bottom:12px}
#exec .xstep{font:inherit;text-align:left;cursor:pointer;display:flex;align-items:center;gap:12px;padding:12px 14px;min-height:76px;background:var(--card);color:var(--ink);border:1px solid var(--rule);border-radius:10px}
#exec .xstep:hover{border-color:var(--rule2);box-shadow:0 2px 8px rgba(16,32,56,.08)}
#exec .xstep:focus-visible{outline:2px solid var(--accent,#1F6FBF);outline-offset:2px}
#exec .xstep .n{font-size:30px;font-weight:700;line-height:1;color:var(--sc);font-variant-numeric:tabular-nums;min-width:1.4em}
#exec .xstep .t{display:grid;gap:2px;min-width:0}
#exec .xstep .t b{font-size:14px;font-weight:600}
#exec .xstep .t span{font-size:12.5px;color:var(--muted);line-height:1.3}
#exec .xmap{margin-bottom:12px}
#exec .xhint{font-weight:400;color:var(--muted)}
#exec .xready{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
#exec .xtile{font:inherit;cursor:pointer;border:0;border-radius:8px;padding:12px 6px;background:var(--tc);color:#fff;display:grid;justify-items:center;gap:2px;text-align:center}
#exec .xtile:hover{filter:brightness(1.08)}
#exec .xtile:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
#exec .xtile .n{font-size:28px;font-weight:700;line-height:1.1}
#exec .xtile .l{font-size:13px}
@media (max-width:820px){#exec .xhow-b{grid-template-columns:minmax(0,1fr)}#exec .xready{grid-template-columns:repeat(2,minmax(0,1fr))}#exec .xmap .c5,#exec .xmap .c7{grid-column:span 12}#exec .xsteps{grid-template-columns:repeat(2,minmax(0,1fr))}#exec .xstep .n{font-size:24px}}
@media (pointer:coarse){#exec .xstep,#exec .xtile{min-height:56px}}
</style>"""

JS_TOP = r"""
// ===== Executive: top of page (how this works, stages, map) =====
const XSTEP_COL = ['#2F76AD', '#008348', '#A2257F', '#7A3E9D', '#C6246B', '#0F6CBD', '#5B4237'];
function renderExecTop()
{
  const sc = count(DATA, d => step(d));
  const col = (s, i) => s[3] || XSTEP_COL[i % XSTEP_COL.length];
  $('x-steps').innerHTML = STEPS.map((s, i) => `<button type="button" class="xstep" style="--sc:${col(s, i)}" data-drill="${esc(JSON.stringify({step: s[0]}))}" aria-label="${esc(s[1])}: ${sc[s[0]] || 0}. ${esc(s[2])}. Show these requests"><span class="n">${sc[s[0]] || 0}</span><span class="t"><b>${esc(s[1])}</b><span>${esc(s[2])}</span></span></button>`).join('');
  $('x-proc').innerHTML = STEPS.map((s, i) => `<li style="--xc:${col(s, i)}"><b>${esc(s[1])}</b><span>${esc(s[2])}.</span></li>`).join('');
  renderMap();
  // Once real Halo data is in, the header stops saying the data is invented.
  const real = DATA.some(d => d.importedAsof), tag = document.querySelector('.hwrap h1 .devtag'), org = $('x-org');
  if (tag) { tag.textContent = real ? 'Halo data' : 'Mock data'; tag.title = real ? 'Requests imported from HaloITSM, with personal details removed' : 'The council, requests, people and dollar figures are all invented' }
  if (org) org.textContent = real ? 'Logan City Council' : 'Wattlebrook City Council';
}
// Strips personal details from imported Halo text. The requester's name (req) is kept on purpose.
function redactText(v)
{
  if (typeof v !== 'string') return v;
  return v
    .replace(/[\w.+-]+@[\w-]+(\.[\w-]+)+/g, '[email removed]')
    .replace(/(?:\+?61[\s-]?|\b0)[2-478](?:[\s-]?\d){8}\b/g, '[phone removed]')
    .replace(/\b(?:13|18)00[\s-]?\d{3}[\s-]?\d{3}\b/g, '[phone removed]')
    .replace(/\b\d{1,5}[A-Za-z]?\s+(?:[A-Z][a-z]+\s){1,3}(?:Street|St|Road|Rd|Avenue|Ave|Drive|Dr|Court|Ct|Place|Pl|Crescent|Cres|Way|Lane|Ln|Parade|Pde|Terrace|Tce|Close|Cl|Highway|Hwy|Boulevard|Bvd|Circuit|Cct)\b\.?/g, '[address removed]')
    .replace(/\b\d{8,}\b/g, '[number removed]');
}
function redactTicket(t)
{
  Object.keys(t).forEach(k => { if (k !== 'id' && k !== 'req' && typeof t[k] === 'string') t[k] = redactText(t[k]) });
  return t;
}
// Once a real Halo export is in, the built-in sample requests make way for it.
function dropSamples()
{
  let n = 0;
  for (let i = DATA.length - 1; i >= 0; i--) { if (DATA[i].gone && !DATA[i].importedAsof) { DATA.splice(i, 1); n++ } }
  if (n) reindex();
  return n;
}
"""


def transform(s):
    if MARK in s:
        return None
    def rep(old, new, count=1):
        nonlocal s
        c = s.count(old)
        assert c == count, f"expected {count} of {old[:70]!r}, found {c}"
        s = s.replace(old, new)

    # 1. Move the map out of Opportunities, into the top of Executive.
    m = re.search(r'<div id="v-map" hidden>\n    <div class="grid">.*?\n    </div>\n  </div>', s, re.S)
    assert m, "v-map block not found"
    s = s[:m.start()] + '<div id="v-map" hidden></div>' + s[m.end():]
    m = re.search(r'(<section class="view" id="exec">\n  <div class="lead">.*?</div></div>\n)', s, re.S)
    assert m, "exec lead not found"
    s = s[:m.end()] + HOW + s[m.end():]
    m = re.search(r'<button type="button" data-view="map" aria-label="Map">.*?</button>', s, re.S)
    assert m, "map button not found"
    s = s[:m.start()] + s[m.end():]

    # 2. Map rendering for Executive: no filter dimming, quadrant labels and tiles drill into Opportunities.
    rep("const dim = filtering() && !matches(d);", "const dim = false;")
    if "{quad: q, view: 'map'}" in s:
        rep("{quad: q, view: 'map'}", "{quad: q, preset: 'live'}")
    rep("${filtering() ? `<b>${pts.filter(d => matches(d)).length}</b> highlighted by the current filters. ` : ''}", "")
    rep('$(\'tiles\').innerHTML = BANDS.map(b => `<button type="button" data-tilefilter="${esc(b[0])}" data-fk="tile-${esc(b[0])}" aria-pressed="${T.band === b[0]}"><span class="n">${bc[b[0]] || 0}</span><span class="l"><i style="background:${b[1]}"></i>${esc(b[0])}</span></button>`).join(\'\');',
        '$(\'tiles\').innerHTML = BANDS.map(b => `<button type="button" class="xtile" style="--tc:${b[1]}" data-drill="${esc(JSON.stringify({band: b[0], preset: \'live\'}))}" data-fk="tile-${esc(b[0])}" aria-label="${esc(b[0])}: ${bc[b[0]] || 0}. Show these requests"><span class="n">${bc[b[0]] || 0}</span><span class="l">${esc(b[0])}</span></button>`).join(\'\');')
    rep("if (VIEW === 'map' && CURRENTTAB === 'opps') renderMap();", "if (CURRENTTAB === 'exec') renderMap();", 2)
    rep("function renderOpps()\n{\n", "function renderOpps()\n{\n  if (VIEW === 'map') VIEW = 'list';\n")
    rep("function renderExec()\n{\n", "function renderExec()\n{\n  renderExecTop();\n")
    i = s.index("function renderExec()")
    s = s[:i] + JS_TOP.lstrip("\n") + "\n" + s[i:]

    # 3. Halo import: redact, then let real data replace the samples (now and on every later load).
    rep("const {tickets, asofIso} = await parseHalo(files);", "const {tickets, asofIso} = await parseHalo(files);\n  tickets.forEach(redactTicket);")
    rep("DATA.forEach(d => { if (!incoming.has(d.id)) { if (!d.gone) gone++; d.gone = true } });",
        "DATA.forEach(d => { if (!incoming.has(d.id)) { if (!d.gone) gone++; d.gone = true } });\n  gone -= dropSamples();")
    rep("if(present.size)DATA.forEach(d=>{d.gone=!present.has(d.id)})}", "if(present.size){DATA.forEach(d=>{d.gone=!present.has(d.id)});dropSamples()}}")
    rep("const gone = Object.keys(TRIAGE).filter(k => !byId[k]);", "const gone = Object.keys(TRIAGE).filter(k => !byId[k] && !(k in PRISTINE));")

    if " · Wattlebrook City Council · " in s:
        rep(" · Wattlebrook City Council · ", ' · <span id="x-org">Wattlebrook City Council</span> · ')
    # 4. CSS: the scatter's styles also apply on Executive.
    # The colour tokens (band colours and so on) are set on the Opportunities root; share them with the map.
    s = s.replace(":is(#opps,#ui){", ":is(#opps,#ui,#exec .xmap){")
    for sel in (".scat", ".dot", ".ql"):
        s = s.replace(":is(#opps,#ui) " + sel, ":is(#opps,#ui,#exec) " + sel)
    i = s.index("</head>") if "</head>" in s[:5000] and False else s.index("<main id=\"main\">")
    s = s[:i] + CSS + s[i:]
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("page"); ap.add_argument("out"); ap.add_argument("--password")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import proto_list as P
    html = open(a.page, encoding="utf-8").read()
    plain, m = (None, None)
    if P.LOCK.search(html):
        if not a.password:
            sys.exit("This page is locked: pass --password")
        plain, m = P.unlock(html, a.password)
    page = plain if plain is not None else html
    new = transform(page)
    if new is None:
        print("already", a.page)
        new = page
    if plain is not None:
        new = P.lock(html, m, new, a.password)
    open(a.out, "w", encoding="utf-8").write(new)
    print("ok", a.out, len(new))


if __name__ == "__main__":
    main()
