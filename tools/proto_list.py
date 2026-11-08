#!/usr/bin/env python3
"""Read or update the AI rapid prototype list held inside the Logan AI pipeline pages.

The list is a JSON block in each page:
  - the standalone list page:        <script type="application/json" id="app-data">
  - the pipeline app copies:          <script type="application/json" id="proto-data">
  - the password-locked copies (current.html / proposed.html): the same pipeline page,
    gzipped and AES-GCM encrypted with a PBKDF2 key from the password.

Usage:
  python3 proto_list.py get <page.html> [--password PW] > data.json
  python3 proto_list.py set <page.html> <data.json> <out.html> [--password PW]
  python3 proto_list.py card <page.html> <out.html> --url URL --name NAME --area AREA --desc TEXT --shot shot.png [--password PW]
    Adds a card (448x280 screenshot thumbnail, "New" badge) to the page's "Prototypes already built"
    grid, or replaces the card with the same URL. Pages without that grid are skipped.

Locked pages need --password. The password is never stored in this file.
"""
import argparse, base64, gzip, json, os, re, sys

BLOCK = re.compile(r'(<script type="application/json" id="(?:app-data|proto-data)">\n?)(.*?)(\n?</script>)', re.S)
LOCK = re.compile(r'const P = (\{.*?\})(?=[,;])', re.S)


def _crypto():
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError:
        sys.exit("Install first: pip install --break-system-packages cryptography")
    return PBKDF2HMAC, hashes, AESGCM


def _key(pw, salt, n):
    PBKDF2HMAC, hashes, _ = _crypto()
    return PBKDF2HMAC(hashes.SHA256(), 32, salt, n).derive(pw.encode())


def unlock(html, pw):
    m = LOCK.search(html)
    if not m:
        return None, None
    P = json.loads(m.group(1))
    _, _, AESGCM = _crypto()
    raw = AESGCM(_key(pw, base64.b64decode(P["s"]), P["n"])).decrypt(
        base64.b64decode(P["i"]), base64.b64decode(P["d"]), None)
    return gzip.decompress(raw).decode(), m


def lock(html_wrapper, m, plain, pw, n=250000):
    _, _, AESGCM = _crypto()
    s, i = os.urandom(16), os.urandom(12)
    d = AESGCM(_key(pw, s, n)).encrypt(i, gzip.compress(plain.encode()), None)
    b = lambda x: base64.b64encode(x).decode()
    P = json.dumps({"s": b(s), "i": b(i), "d": b(d), "n": n}, separators=(",", ":"))
    out = html_wrapper[:m.start(1)] + P + html_wrapper[m.end(1):]
    assert unlock(out, pw)[0] == plain, "round trip failed"
    return out


def get_data(page):
    m = BLOCK.search(page)
    if not m:
        sys.exit("No app-data or proto-data block found")
    return json.loads(m.group(2))


def set_data(page, data):
    m = BLOCK.search(page)
    if not m:
        sys.exit("No app-data or proto-data block found")
    body = json.dumps(data, indent=1, ensure_ascii=False).replace("</", "<\\/")
    return page[:m.start(2)] + body + page[m.end(2):]


GO_SVG = ('<svg viewBox="0 0 16 16" aria-hidden="true" width="12" height="12"><path d="M6 3H3v10h10v-3M9 3h4v4M13 3 7 9" '
          'fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>')


def shot_data_uri(path):
    """Screenshot (any size, ideally 1280x800) -> 448x280 progressive JPEG data URI, cropped from the top."""
    try:
        from PIL import Image
    except ImportError:
        sys.exit("Install first: pip install --break-system-packages Pillow")
    import io
    im = Image.open(path).convert("RGB")
    w, h = im.size
    want = 280 / 448
    if h / w > want:
        im = im.crop((0, 0, w, int(w * want)))
    else:
        nw = int(h / want)
        im = im.crop((0, 0, nw, h))
    im = im.resize((448, 280), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=72, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;").replace("'", "&#x27;"))


def add_card(page, url, name, area, desc, shot):
    """Add (or replace, matched by url) a card in the 'Prototypes already built' grid."""
    g = page.find('<div class="bgrid">')
    if g < 0:
        return page, False
    end = page.find("</div>", g)
    img = (f'<span class="bshot"><img src="{shot_data_uri(shot)}" alt="" width="448" height="280"></span>' if shot
           else '<span class="bshot none" aria-hidden="true">No preview</span>')
    card = (f'<a class="bcard" href="{esc(url)}" target="_blank" rel="noopener">{img}'
            f'<span class="btop"><span class="barea">{esc(area)}</span><span class="bnew">New</span></span>'
            f'<b class="bname">{esc(name)}</b><span class="bdesc">{esc(desc)}</span>'
            f'<span class="bgo">Open{GO_SVG}<span class="vh"> {esc(name)} (opens in a new tab)</span></span></a>')
    grid = page[g:end]
    old = re.search(r'<a class="bcard" href="' + re.escape(esc(url)) + r'".*?</a>', grid, re.S)
    grid = grid[:old.start()] + card + grid[old.end():] if old else grid + card
    page = page[:g] + grid + page[end:]
    n = len(re.findall(r'<a class="bcard"', page[g:page.find("</div>", g)]))
    page = re.sub(r'(<span class="bcount">)\d+(</span>)', lambda m: f"{m.group(1)}{n}{m.group(2)}", page, count=1)
    return page, True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["get", "set", "card"])
    ap.add_argument("page")
    ap.add_argument("data", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--password")
    ap.add_argument("--url"); ap.add_argument("--name"); ap.add_argument("--area")
    ap.add_argument("--desc"); ap.add_argument("--shot")
    a = ap.parse_args()
    if a.cmd == "card":
        # usage: card <page> <out> --url --name --area --desc --shot shot.png [--password]
        a.out, a.data = a.data, None
    html = open(a.page, encoding="utf-8").read()
    plain, m = (None, None)
    if LOCK.search(html):
        if not a.password:
            sys.exit("This page is locked: pass --password")
        plain, m = unlock(html, a.password)
    page = plain if plain is not None else html
    if a.cmd == "get":
        print(json.dumps(get_data(page), indent=1, ensure_ascii=False))
        return
    if a.cmd == "card":
        if not (a.out and a.url and a.name and a.area and a.desc):
            sys.exit("card needs <out.html> --url --name --area --desc [--shot shot.png]")
        new, ok = add_card(page, a.url, a.name, a.area, a.desc, a.shot)
        if not ok:
            print("skip: no 'Prototypes already built' grid in this page")
            return
        if plain is not None:
            new = lock(html, m, new, a.password)
        open(a.out, "w", encoding="utf-8").write(new)
        print("ok", a.out, len(new))
        return
    if not (a.data and a.out):
        sys.exit("set needs <data.json> <out.html>")
    data = json.load(open(a.data, encoding="utf-8"))
    for k in ("apps", "reviewed"):
        assert isinstance(data.get(k), list), f"data.{k} must be a list"
    new = set_data(page, data)
    if plain is not None:
        new = lock(html, m, new, a.password)
    open(a.out, "w", encoding="utf-8").write(new)
    print("ok", a.out, len(new))


if __name__ == "__main__":
    main()
