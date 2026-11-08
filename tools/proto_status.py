#!/usr/bin/env python3
"""Background tracker for the Logan AI prototype list.

Publishing artifacts can fail (for example the daily publish limit). This file keeps track of which
apps are done, and which list copies still need the update, in ai-pipeline/status.json in this repo,
so nothing depends on a publish going through. Commit and push status.json after every change.

Usage (run from the repo root):
  python3 tools/proto_status.py mark APP-08 --status Built --url <app url> --version 1 \
      --lastUpdated 2026-11-08 --notes "..." --runs 1 --name "Engineering Project Writer" \
      --area Transport --desc "Card text" --shot shot.png
      Records (or updates) an app's result. Every list copy starts as pending. --shot keeps a small
      448x280 copy of the screenshot at ai-pipeline/shots/<APP id>.jpg so a later run can add the card.
  python3 tools/proto_status.py done APP-08 list polish mock github preview
      Marks list copies as updated for that app.
  python3 tools/proto_status.py apply data.json [out.json]
      Copies the tracked fields (status, url, version, lastUpdated, notes, runs) onto the matching
      apps in a list data file, so a run that reads the list page sees apps that are already built.
      Only fields where the tracker is newer (lastUpdated) or the list still says "Not built" change.
  python3 tools/proto_status.py pending
      Prints the apps whose list copies are not all updated yet, as JSON.

List copies: list (the list page), polish (copy a), mock (copy b), github (copy d), preview (copy c).
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "..", "ai-pipeline", "status.json")
PLACES = ["list", "polish", "mock", "github", "preview"]
FIELDS = ["status", "url", "version", "lastUpdated", "notes", "runs"]


def load():
    """Read the tracker, or an empty one if it does not exist yet."""
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as f:
            return json.load(f)
    return {"about": "Background tracker for the AI prototype list. See tools/proto_status.py.", "apps": {}}


def save(st):
    """Write the tracker with stable formatting so diffs stay small."""
    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def save_shot(app, src):
    """Keep a 448x280 JPEG of the screenshot (cropped from the top) beside the tracker."""
    from PIL import Image
    im = Image.open(src).convert("RGB")
    w, h = im.size
    if h / w > 280 / 448:
        im = im.crop((0, 0, w, int(w * 280 / 448)))
    else:
        im = im.crop((0, 0, int(h * 448 / 280), h))
    rel = "ai-pipeline/shots/" + app + ".jpg"
    out = os.path.join(HERE, "..", rel)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    im.resize((448, 280), Image.LANCZOS).save(out, "JPEG", quality=80, optimize=True)
    return rel


def cmd_mark(a):
    st = load()
    rec = st["apps"].get(a.app, {})
    for k in FIELDS + ["name", "area", "desc"]:
        v = getattr(a, k)
        if v is not None:
            rec[k] = int(v) if k == "runs" else v
    if a.shot:
        rec["shot"] = save_shot(a.app, a.shot)
    rec["places"] = {p: False for p in PLACES}
    st["apps"][a.app] = rec
    save(st)
    print("marked", a.app, rec.get("status"))


def cmd_done(a):
    st = load()
    rec = st["apps"].get(a.app)
    if not rec:
        sys.exit("No tracked record for " + a.app)
    for p in a.places:
        if p not in PLACES:
            sys.exit("Unknown place " + p + " (use " + ", ".join(PLACES) + ")")
        rec.setdefault("places", {})[p] = True
    save(st)
    print(a.app, rec["places"])


def cmd_apply(a):
    st = load()
    with open(a.data, encoding="utf-8") as f:
        data = json.load(f)
    changed = []
    for app in data.get("apps", []):
        rec = st["apps"].get(app.get("id"))
        if not rec:
            continue
        newer = str(rec.get("lastUpdated", "")) >= str(app.get("lastUpdated", "")) or app.get("status") == "Not built"
        if newer and any(app.get(k) != rec[k] for k in FIELDS if k in rec):
            for k in FIELDS:
                if k in rec:
                    app[k] = rec[k]
            changed.append(app["id"])
    with open(a.out or a.data, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    print("applied", changed)


def cmd_pending(a):
    st = load()
    out = {k: [p for p in PLACES if not v.get("places", {}).get(p)] for k, v in st["apps"].items()}
    print(json.dumps({k: v for k, v in out.items() if v}, indent=1))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("mark"); m.add_argument("app"); m.add_argument("--shot")
    for k in FIELDS + ["name", "area", "desc"]:
        m.add_argument("--" + k)
    d = sub.add_parser("done"); d.add_argument("app"); d.add_argument("places", nargs="+")
    p = sub.add_parser("apply"); p.add_argument("data"); p.add_argument("out", nargs="?")
    sub.add_parser("pending")
    a = ap.parse_args()
    {"mark": cmd_mark, "done": cmd_done, "apply": cmd_apply, "pending": cmd_pending}[a.cmd](a)


if __name__ == "__main__":
    main()
