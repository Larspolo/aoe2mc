#!/usr/bin/env python3
"""
Find and download reference images of the game from the AoE2 wiki (MediaWiki API), as PNG.

Usage:
    python3 tools/refimage.py search "house aoe2DE"                 # list file names
    python3 tools/refimage.py get "House Castle DE AoE2DE.png" OUT.png

The wiki HTML pages give a Cloudflare challenge (403); the API and the image server work.
"""
import argparse
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from PIL import Image

from agent_config import CONFIG

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
    a = ap.parse_args()
    if a.cmd == "search":
        print("\n".join(search(a.text)))
    else:
        w, h = get(a.name, a.out)
        print(f"Wrote {a.out}: {w}x{h} pixels")


if __name__ == "__main__":
    main()
