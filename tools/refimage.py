#!/usr/bin/env python3
"""
Find and download reference images of the game from the AoE2 wiki (MediaWiki API), as PNG.

Usage:
    python3 tools/refimage.py search "house aoe2DE"                 # list file names
    python3 tools/refimage.py get "House Castle DE AoE2DE.png" OUT.png
    python3 tools/refimage.py box "Hoplite (Age of Empires)" Toolworking  # the infobox values: one JSON line per page

The wiki HTML pages give a Cloudflare challenge (403); the API and the image server work.
"""
import argparse
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "framework", "tools"))
from agent_config import CONFIG  # noqa: E402

API = "https://ageofempires.fandom.com/api.php"
HEADERS = {"User-Agent": f"aoe2mc-refimage/1.0 (https://github.com/{CONFIG['repo']})"}   # the default urllib agent gets 403


def fetch(url, timeout=30, tries=4):
    for k in range(tries):          # the image host sometimes gives 503 for some seconds (#456)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code < 500 or k == tries - 1:
                raise
            time.sleep(5 * (k + 1))


def query(**params):
    """The API result of params; action="parse" (the wikitext of a page) gives the "parse" part (#2685)."""
    params = dict(action="query", format="json") | params
    return json.loads(fetch(API + "?" + urllib.parse.urlencode(params)))[params["action"]]


def search(text, limit=30):
    """File names (without "File:") that match the text."""
    hits = query(list="search", srnamespace=6, srsearch=text, srlimit=limit)["search"]
    return [h["title"].split(":", 1)[1] for h in hits]


CLEAN = ((r"\[\[File:[^]]*\]\]\s*", ""), (r"\{\{\w*icons\|([^|}]*)[^}]*\}\}", r"\1"),   # box(): markup -> text
         (r"\{\{tt\|([^|}]*)[^}]*\}\}", r"\1"), (r"<br\s*/?>", ", "), (r"\[\[(?:[^]|]*\|)?([^]]*)\]\]", r"\1"),
         (r"'{2,}", ""))


def box(text):
    """The values of the first infobox ("{{Infobox ...", "{{Techbox") of a wikitext, as plain text: an icon or a link
    gives its name, "{{tt|A|B}}" gives A, "{{resources|food = 60}}" gives "60 food", "<br />" gives ", " (#3665)."""
    i = min((k for k in (text.find("{{Infobox"), text.find("{{Techbox")) if k >= 0), default=-1)
    if i < 0:
        return {}
    depth, j = 0, i
    while j < len(text) and (depth or j == i):                         # the end of the template: its own "}}"
        two = text[j:j + 2]
        depth += {"{{": 1, "}}": -1}.get(two, 0)
        j += 2 if two in ("{{", "}}") else 1
    out = {}
    for m in re.finditer(r"^\|\s*(\w+)\s*=(.*)$", text[i:j - 2], re.M):
        v = m.group(2)
        for a, b in CLEAN:
            v = re.sub(a, b, v)
        v = re.sub(r"\{\{[Rr]esources\|([^}]*)\}\}", lambda r: ", ".join(
            f"{x.split('=')[1].strip()} {x.split('=')[0].strip()}" for x in r.group(1).split("|") if "=" in x), v)
        out[m.group(1)] = v.strip()
    return out


def page(name):
    """The wikitext of the page name (redirects followed), or None when the page does not exist."""
    p = dict(action="parse", page=name, prop="wikitext", redirects=1, format="json")
    return json.loads(fetch(API + "?" + urllib.parse.urlencode(p))).get("parse", {}).get("wikitext", {}).get("*")


def get(name, out):
    """Download one file of the wiki and save it as PNG. Return the image size."""
    name = name if name.startswith("File:") else "File:" + name
    page = next(iter(query(titles=name, prop="imageinfo", iiprop="url")["pages"].values()))
    if "imageinfo" not in page:
        raise SystemExit(f"{name}: not on the wiki (use 'search')")
    img = Image.open(io.BytesIO(fetch(page["imageinfo"][0]["url"], 60)))      # the server sends WebP
    img.save(out)
    return img.size


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[1].strip())
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("text")
    g = sub.add_parser("get")
    g.add_argument("name")
    g.add_argument("out")
    b = sub.add_parser("box", help="print the infobox values of each page as one JSON line")
    b.add_argument("pages", nargs="+")
    a = ap.parse_args()
    if a.cmd == "search":
        print("\n".join(search(a.text)))
    elif a.cmd == "box":
        for name in a.pages:
            text = page(name)
            print(json.dumps({"page": name} | (box(text) if text else {"missing": True}), ensure_ascii=False))
    else:
        w, h = get(a.name, a.out)
        print(f"Wrote {a.out}: {w}x{h} pixels")


if __name__ == "__main__":
    main()
