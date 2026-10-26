"""Garrisoned units stand inside their building, invulnerable and without a visible name (#807)."""
import json
import os

import pytest
from test_garrison import convert, garrison_map, villagers

import aoe2mc
import buildings


@pytest.fixture(scope="module")
def inside(tmp_path_factory):
    d = tmp_path_factory.mktemp("inside")
    src = garrison_map(str(d / "g.aoe2scenario"))
    w, log = convert(src, str(d / "W"))
    return w, log, json.load(open(os.path.join(str(d / "W"), "aoe2mc.json")))


def test_garrisoned_units_stand_inside_the_town_center(inside):
    w, log, _ = inside
    assert "  units in a block (moved up): 0" in log
    assert "  units (garrisoned, inside the holder): 3" in log
    half = buildings.footprint("TOWN_CENTER") * 4 / 2
    vs = villagers(w)
    held = [e for e in vs if "aoe2mc.garrisoned" in [str(t) for t in e.get("Tags", [])]]
    assert len(vs) == 4 and len(held) == 3
    for e in held:
        x, y, z = (float(v) for v in e["Pos"])
        assert max(abs(x - 32), abs(z - 32)) < half                     # inside the footprint
        assert e["Invulnerable"] == 1 and e["NoAI"] == 1 and e["CustomNameVisible"] == 0
        assert w.block(int(x), int(y) - 1, int(z)).split("[")[0] not in ("minecraft:air", "minecraft:barrier")
        for dy in (0, 1):                                               # free space of a room
            st = w.block(int(x), int(y) + dy, int(z))
            assert st == "minecraft:barrier" or aoe2mc.passable_states([st])[0], st
    assert len({tuple(float(v) for v in e["Pos"]) for e in held}) == 3  # each on its own cell
    free = next(e for e in vs if e not in held)
    assert free["CustomNameVisible"] == 1 and free.get("Invulnerable", 0) == 0
    assert abs(float(free["Pos"][0]) - 14) < 4                          # the villager outside does not move


def test_the_json_names_the_holder(inside):
    _, _, data = inside
    tc = next(o for o in data["objects"] if o["name"] == "TOWN_CENTER")
    held = [o for o in data["objects"] if o.get("holder") is not None]
    assert len(held) == 3 and all(o["holder"] == tc["ref"] and "uuid" in o for o in held)


@pytest.mark.mc
def test_garrisoned_units_stay_alive_on_a_server(tmp_path):
    import re
    import time

    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import run
    src = garrison_map(str(tmp_path / "g.aoe2scenario"))
    convert(src, str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    uuids = [o["uuid"] for o in data["objects"] if o.get("holder") is not None]
    with run.Game(str(tmp_path / "W")) as game:
        game.forceload()

        def state():
            time.sleep(1)
            n = re.search(r"Count: (\d+)", game.command("execute if entity @e[tag=aoe2mc.garrisoned]"))
            return int(n[1]) if n else 0, [game.command(f"data get entity {u} Pos") for u in uuids]
        for _ in range(20):                                             # the entities load after the chunks
            n, pos = state()
            if n == 3:
                break
        time.sleep(60)
        assert state() == (3, pos) and all("entity data" in p for p in pos), pos
