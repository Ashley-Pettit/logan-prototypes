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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["get", "set"])
    ap.add_argument("page")
    ap.add_argument("data", nargs="?")
    ap.add_argument("out", nargs="?")
    ap.add_argument("--password")
    a = ap.parse_args()
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
