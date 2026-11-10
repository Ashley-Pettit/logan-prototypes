#!/usr/bin/env python3
"""Bundle Logan AI prototype apps inside a pipeline artifact, so sharing the pipeline shares the apps.

Why: a claude.ai artifact shared with someone does not share the other artifacts it links to.
Copies of the apps published as extra files of the pipeline artifact open for anyone who can open
the pipeline, and they keep working with AI (the pipeline must declare the `sample` capability,
plus `downloads` for apps that save files).

How it works:
  - Each app is published in the pipeline artifact as  app-<artifactId>.html  (a full HTML document).
  - apps.json (published beside it) lists the bundled artifact ids.
  - A small script added to the pipeline page and to every bundled app catches clicks on links to
    https://claude.ai/artifact/<id> and, when <id> is bundled, opens the local copy in the same frame.
    Links to apps that are not bundled open as before.
  - In each bundled app the "All AI prototypes" link goes back to the pipeline's AI playground (./#ai-prototypes).

Usage:
  python3 bundle_apps.py prepare <app.html> <artifactId> <outdir>   writes <outdir>/app-<artifactId>.html
  python3 bundle_apps.py manifest <outdir>                           writes <outdir>/apps.json from the app-*.html files there
  python3 bundle_apps.py inject <pipeline.html> <out.html>           adds or refreshes the link script in the pipeline page

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
  var ids = null;
  fetch('apps.json', {cache: 'no-store'}).then(function(r){ return r.ok ? r.json() : null; })
    .then(function(j){ ids = new Set((j && j.apps) || []); }).catch(function(){ ids = new Set(); });
  document.addEventListener('click', function(e){
    if (!ids || e.defaultPrevented || e.button !== 0) return;
    var a = e.target.closest && e.target.closest('a[href]'); if (!a) return;
    var m = String(a.href).match(/^https:\/\/claude\.ai\/(?:code\/)?artifact\/([A-Za-z0-9-]+)\/?(#[A-Za-z0-9_-]*)?$/);
    if (!m || !ids.has(m[1])) return;
    e.preventDefault(); e.stopPropagation();
    location.href = 'app-' + m[1] + '.html' + (m[2] || '');
  }, true);
})();
"""


def block():
    return f"{START}\n<script>{JS}</script>\n{END}"


def put_block(page):
    if START in page:
        s, e = page.index(START), page.index(END) + len(END)
        return page[:s] + block() + page[e:]
    i = page.rfind("</body>")
    return page[:i] + block() + "\n" + page[i:] if i > -1 else page + "\n" + block()


def prepare(src, art_id, outdir):
    page = open(src, encoding="utf-8").read()
    if not page.lstrip().lower().startswith("<!doctype"):
        page = SKELETON + page + "\n</body></html>\n"
    # "All AI prototypes" goes back to the pipeline page this copy lives in.
    page = re.sub(r'(<a id="lpx-protos-btn" href=")https://claude\.ai/artifact/[A-Za-z0-9-]+(#ai-prototypes)?(")(?: target="_blank" rel="noopener")?',
                  r'\1./#ai-prototypes\3', page)
    page = put_block(page)
    os.makedirs(outdir, exist_ok=True)
    out = os.path.join(outdir, f"app-{art_id}.html")
    open(out, "w", encoding="utf-8").write(page)
    return out


def manifest(outdir):
    ids = sorted(f[4:-5] for f in os.listdir(outdir) if f.startswith("app-") and f.endswith(".html"))
    out = os.path.join(outdir, "apps.json")
    json.dump({"apps": ids}, open(out, "w"), indent=1)
    return out, len(ids)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["prepare"] and len(a) == 4:
        print(prepare(a[1], a[2], a[3]))
    elif a[:1] == ["manifest"] and len(a) == 2:
        print(*manifest(a[1]))
    elif a[:1] == ["inject"] and len(a) == 3:
        open(a[2], "w", encoding="utf-8").write(put_block(open(a[1], encoding="utf-8").read()))
        print("ok", a[2])
    else:
        sys.exit(__doc__)
