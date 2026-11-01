"""The lang files of the unit, building and technology names in the other AoE2 DE languages, from the string tables
of the AoE2 DE install on this computer (#5435, decision #5378). The repository and the bundles have no AoE2 text:
the tool reads the texts on the computer of the player and adds them to the resource pack of one world.

A name of game/lang.name() has no string ID in the data: the tool finds the English name in the English table of the
install and takes the text of the same ID in each other language. A name with no exact English string keeps the
English fallback of the client.

    python3 tools/aoe2_lang.py RESOURCES WORLD

RESOURCES: the folder `resources` of the AoE2 DE install (it has <lang>/strings/key-value/). WORLD: a world converted
with --resource-pack. Do not share a world with these files without the notice of the Microsoft Game Content Usage
Rules: https://www.xbox.com/en-US/developers/rules"""
import argparse
import glob
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path[:0] = [ROOT, os.path.join(ROOT, "game")]
LANGS = os.path.join(ROOT, "data", "aoe2_langs.jsonl")              # AoE2 DE language folder -> Minecraft code
LINE = re.compile(r'^\s*(\d+)\s+"(.*)"\s*$')
PACK = os.path.join("resourcepacks", "resources.zip")


def read_table(path):
    """{string ID: text} of one key-value file (lines `ID "text"`; `//` comments and other lines are skipped)."""
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        for s in f:
            if m := LINE.match(s):
                out[m[1]] = m[2].replace('\\"', '"')
    return out


def tables(resources, folder):
    """The joined key-value tables of the language folder of the install."""
    out = {}
    for p in sorted(glob.glob(os.path.join(str(resources), folder, "strings", "key-value", "*.txt"))):
        out |= read_table(p)
    return out


def names():
    """{translate key of game/lang.name(): English name}: the units and buildings of game/data (units.pretty) and the
    menu items of game/data/train.jsonl (their label)."""
    import table

    from units import pretty
    out = {f"aoe2mc.unit.{r['name']}": pretty(r["name"]) for f in ("units.jsonl", "buildings.jsonl")
           for r in table.load(f)}
    return out | {f"aoe2mc.tech.{r['name']}": r["label"] for r in table.load("train.jsonl") if r.get("label")}


def lang_files(resources, langs=None):
    """{Minecraft code: {key: text}} for each language of the install other than English."""
    if langs is None:
        with open(LANGS, encoding="utf-8") as f:
            langs = {r["name"]: r["code"] for r in map(json.loads, f) if r}
    ids = {}
    for i, text in tables(resources, "en").items():
        ids.setdefault(text, i)                                      # the first ID of a text
    keys = {k: ids[v] for k, v in names().items() if v in ids}
    out = {}
    for folder, code in sorted(langs.items()):
        if folder == "en" or not (t := tables(resources, folder)):
            continue
        if found := {k: t[i] for k, i in sorted(keys.items()) if t.get(i)}:
            out[code] = found
    return out


def add_to_pack(pack, files):
    """Merge the lang files into assets/aoe2mc/lang/ of the zip `pack` (the other files stay the same)."""
    with zipfile.ZipFile(pack) as z:
        old = {n: z.read(n) for n in z.namelist()}
    for code, rows in files.items():
        name = f"assets/aoe2mc/lang/{code}.json"
        old[name] = json.dumps(json.loads(old.get(name, b"{}")) | rows, indent=1, sort_keys=True,
                               ensure_ascii=False).encode()
    with zipfile.ZipFile(pack, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in old.items():
            z.writestr(n, b)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("resources", help="the folder `resources` of the AoE2 DE install")
    ap.add_argument("world", help="a world converted with --resource-pack")
    a = ap.parse_args(argv)
    pack = os.path.join(a.world, PACK)
    if not os.path.isfile(pack):
        ap.error(f"{pack}: no resource pack; convert the world with --resource-pack")
    files = lang_files(a.resources)
    if not files:
        ap.error(f"{a.resources}: no string tables (<lang>/strings/key-value/*.txt) with the names")
    add_to_pack(pack, files)
    print(f"{pack}: {', '.join(f'{c} {len(r)}' for c, r in sorted(files.items()))} names. Do not share the world "
          "without the notice of the Game Content Usage Rules: https://www.xbox.com/en-US/developers/rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
