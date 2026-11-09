#!/usr/bin/env python3
"""Keep the pipeline app's bottom tab bar still on iPhone.

On phones the AI & Automation Pipeline shows its tabs as a bar fixed to the bottom of the page.
iPhones move fixed bars as the browser or app toolbars grow and shrink while scrolling. This
moves the page content into its own scrolling area and puts the tab bar below it, so the bar
never moves. Desktop is untouched. Idempotent.

Usage: python3 ios_footer.py <page.html> <out.html>
"""
import sys

START, END = "<!-- lpx-footfix:start -->", "<!-- lpx-footfix:end -->"
BLOCK = r"""<!-- lpx-footfix:start -->
<style id="lpx-footfix-css">
html.lpx-ff,html.lpx-ff body{height:100%;overflow:hidden;overscroll-behavior:none}
html.lpx-ff{padding-bottom:0!important}
html.lpx-ff body{display:flex;flex-direction:column;height:100vh;height:100dvh;padding-bottom:0!important;margin:0}
#lpx-scroller{flex:1 1 auto;min-height:0;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior-y:contain}
html.lpx-ff #tabs{position:relative!important;left:auto!important;right:auto!important;bottom:auto!important;flex:none;width:auto}
</style>
<script>
(function(){
  if (window.__lpxFootFix) return; window.__lpxFootFix = true;
  var mq = window.matchMedia('(max-width: 820px)');
  var sc = null, home = null, realScrollTo = window.scrollTo.bind(window);
  var SKIP = {SCRIPT: 1, STYLE: 1, TEMPLATE: 1};
  function on(){
    var tabs = document.getElementById('tabs'); if (!tabs || sc) return;
    home = {parent: tabs.parentNode, next: tabs.nextSibling};
    sc = document.createElement('div'); sc.id = 'lpx-scroller';
    Array.prototype.slice.call(document.body.childNodes).forEach(function(n){
      if (n.nodeType === 1 && (SKIP[n.tagName] || n.id === 'lpx-prod' || n.id === 'lpx-ol-toast')) return;
      sc.appendChild(n);
    });
    document.body.insertBefore(sc, document.body.firstChild);
    document.body.insertBefore(tabs, sc.nextSibling);
    document.documentElement.classList.add('lpx-ff');
    window.scrollTo = function(a, b){
      if (a && typeof a === 'object') sc.scrollTo(a); else sc.scrollTo(a || 0, b || 0);
    };
  }
  function off(){
    if (!sc) return;
    var tabs = document.getElementById('tabs');
    while (sc.firstChild) document.body.insertBefore(sc.firstChild, sc);
    sc.remove(); sc = null;
    if (tabs && home && home.parent) home.parent.insertBefore(tabs, home.next && home.next.parentNode === home.parent ? home.next : null);
    document.documentElement.classList.remove('lpx-ff');
    window.scrollTo = realScrollTo;
  }
  function apply(){ if (mq.matches) on(); else off(); }
  function boot(){ apply(); if (mq.addEventListener) mq.addEventListener('change', apply); else if (mq.addListener) mq.addListener(apply); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
</script>
<!-- lpx-footfix:end -->"""


def inject(page):
    if START in page:
        s, e = page.index(START), page.index(END) + len(END)
        return page[:s] + BLOCK + page[e:]
    i = page.rfind("</body>")
    return page[:i] + BLOCK + "\n" + page[i:] if i > -1 else page + "\n" + BLOCK


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    page = open(sys.argv[1], encoding="utf-8").read()  # read first, so the same file can be input and output
    out = inject(page)
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        f.write(out)
    print("ok", sys.argv[2])
