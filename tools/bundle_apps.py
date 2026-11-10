#!/usr/bin/env python3
"""Bundle Logan AI prototype apps inside a pipeline artifact, so sharing the pipeline shares the apps.

Why: a claude.ai artifact shared with someone does not share the other artifacts it links to.
Copies of the apps published as extra files of the pipeline artifact open for anyone who can open
the pipeline, and they keep working with AI (the pipeline must declare the `sample` capability,
plus `downloads` for apps that save files).

How it works:
  - Each app is published in the pipeline artifact as  app-<artifactId>.html  (a full HTML document).
  - apps.json (published beside it) lists the bundled artifact ids.
  - A small script added to the pipeline page and to every bundled app rewrites links to
    https://claude.ai/artifact/<id>, when <id> is bundled, into plain same-frame links to app-<id>.html
    (the bundled ids are written into the script; no fetch, no click interception, since the artifact
    host may block both). Links to apps that are not bundled open as before.
  - In each bundled app the "All AI prototypes" link goes back to the pipeline's AI playground (./#ai-prototypes).

Usage:
  python3 bundle_apps.py prepare <app.html> <artifactId> <outdir>   writes <outdir>/app-<artifactId>.html
  python3 bundle_apps.py manifest <outdir>                           writes apps.json and adds the link script to every app there
  python3 bundle_apps.py inject <pipeline.html> <out.html> <outdir>  adds or refreshes the link script in the pipeline page

Publish with the Artifact tool: file_path = the pipeline page, url = the pipeline artifact, and
files = {"apps.json": "<outdir>/apps.json", "app-<id>.html": "<outdir>/app-<id>.html", ...}.
To refresh one app later, publish the pipeline page unchanged with files = {"app-<id>.html": ..., "apps.json": ...};
files left out are kept.
"""
import json, os, re, sys

START, END = "<!-- lpx-bundle:start -->", "<!-- lpx-bundle:end -->"
SKELETON = ('<!doctype html><html lang="en-AU"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>\n')

JS = r"""
(function(){
  if (window.__lpxBundle) return; window.__lpxBundle = true;
  var ids = new Set(__IDS__);
  var re = /^https:\/\/claude\.ai\/(?:code\/)?artifact\/([A-Za-z0-9-]+)\/?(#[A-Za-z0-9_-]*)?$/;
  // Point links to bundled apps at the copy inside this artifact, as plain same-frame links.
  function fix(a){
    var h = a.getAttribute('href'); if (!h) return;
    var m = h.match(re); if (!m || !ids.has(m[1])) return;
    a.setAttribute('href', 'app-' + m[1] + '.html' + (m[2] || ''));
    a.removeAttribute('target'); a.removeAttribute('rel');
    a.querySelectorAll('.vh').forEach(function(v){ v.textContent = v.textContent.replace(/\s*\(opens in a new tab\)/, ''); });
  }
  function scan(n){ if (n.matches && n.matches('a[href]')) fix(n); if (n.querySelectorAll) n.querySelectorAll('a[href]').forEach(fix); }
  scan(document);
  new MutationObserver(function(ms){ ms.forEach(function(m){
    if (m.type === 'attributes') fix(m.target);
    else m.addedNodes.forEach(function(n){ if (n.nodeType === 1) scan(n); });
  }); }).observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['href']});
})();
"""


def block(ids):
    return f"{START}\n<script>{JS.replace('__IDS__', json.dumps(sorted(ids)))}</script>\n{END}"


def put_block(page, ids):
    if START in page:
        s, e = page.index(START), page.index(END) + len(END)
        return page[:s] + block(ids) + page[e:]
    i = page.rfind("</body>")
    return page[:i] + block(ids) + "\n" + page[i:] if i > -1 else page + "\n" + block(ids)


def ids_in(outdir):
    return sorted(f[4:-5] for f in os.listdir(outdir) if f.startswith("app-") and f.endswith(".html"))


def prepare(src, art_id, outdir):
    page = open(src, encoding="utf-8").read()
    if not page.lstrip().lower().startswith("<!doctype"):
        page = SKELETON + page + "\n</body></html>\n"
    # "All AI prototypes" goes back to the pipeline page this copy lives in.
    page = re.sub(r'(<a id="lpx-protos-btn" href=")https://claude\.ai/artifact/[A-Za-z0-9-]+(#ai-prototypes)?(")(?: target="_blank" rel="noopener")?',
                  r'\1./#ai-prototypes\3', page)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"app-{art_id}.html")
    open(out, "w", encoding="utf-8").write(page)
    return out


def manifest(outdir):
    """Write apps.json and put the link script (with the bundled ids inline) into every bundled app."""
    ids = ids_in(outdir)
    for i in ids:
        f = os.path.join(outdir, f"app-{i}.html")
        page = open(f, encoding="utf-8").read()
        open(f, "w", encoding="utf-8").write(put_block(page, ids))
    out = os.path.join(outdir, "apps.json")
    json.dump({"apps": ids}, open(out, "w"), indent=1)
    return out, len(ids)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["prepare"] and len(a) == 4:
        print(prepare(a[1], a[2], a[3]))
    elif a[:1] == ["manifest"] and len(a) == 2:
        print(*manifest(a[1]))
    elif a[:1] == ["inject"] and len(a) == 4:
        page = open(a[1], encoding="utf-8").read()  # read before opening the output, which may be the same file
        open(a[2], "w", encoding="utf-8").write(put_block(page, ids_in(a[3])))
        print("ok", a[2])
    else:
        sys.exit(__doc__)
