"""The advancement tab "Age of Empires II" of the datapack (#5278): root.json and one advancement per line of
data/achievements.jsonl, each with the trigger minecraft:impossible and a parent that exists. Form only: the keys come
from the data file."""
import json
import os

import aoe2mc

FORM = {"name": str, "title": str, "description": str, "icon": str, "parent": str, "event": str}


def test_each_line_has_the_form_and_a_known_parent():
    names = [r["name"] for r in aoe2mc.ACHIEVEMENTS]
    assert len(names) == len(set(names))
    for r in aoe2mc.ACHIEVEMENTS:
        assert set(r) == set(FORM) and all(isinstance(r[k], t) for k, t in FORM.items()), r
        assert r["icon"].startswith("minecraft:") and (r["parent"] == "root" or r["parent"] in names), r


def test_the_world_has_the_tab_and_one_file_per_line(tiny_world):
    folder = os.path.join(tiny_world[0], "datapacks", "aoe2mc", "data", "aoe2mc", "advancement")
    files = {f[:-5]: json.load(open(os.path.join(folder, f))) for f in os.listdir(folder)}
    assert set(files) == {"root"} | {r["name"].lower() for r in aoe2mc.ACHIEVEMENTS}
    root = files.pop("root")
    assert "parent" not in root and root["display"]["background"] and root["display"]["show_toast"] is False
    for name, a in files.items():
        assert [c["trigger"] for c in a["criteria"].values()] == ["minecraft:impossible"], name
        assert a["parent"].split(":")[1] in files or a["parent"] == "aoe2mc:root", name


def test_test_rows_give_their_files():
    row = {"name": "TEST_WIN", "title": "T", "description": "D", "icon": "minecraft:stone", "parent": "root",
           "event": "win all"}
    out = aoe2mc.advancement_files([row])
    assert set(out) == {"data/aoe2mc/advancement/root.json", "data/aoe2mc/advancement/test_win.json"}
    assert out["data/aoe2mc/advancement/test_win.json"]["display"]["title"] == {"text": "T"}
