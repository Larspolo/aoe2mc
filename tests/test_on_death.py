"""A dead Konnik rises as a Dismounted Konnik at its place (#4471, AoE2 DE wiki "Konnik": "Turn into a(n) (Elite)
Dismounted Konnik upon death"): the key "on_death", combat.on_death_command, the marker of AoePlugin.onDeath and
train.fell / train.risen. Test data on a fake server, and a death on a server."""
import json
import shutil
import time

import combat as inner  # the module that game/train.py imports (game/ is on sys.path)
import pytest
from test_castle_upgrades import setup

from game import combat, gather, run, savegame, train

MARKER = "@e[type=marker,tag=aoe2mc.fell.l,limit=1]"                 # the marker of the plugin for unit "l"


def keys(monkeypatch, table):
    for m in (combat, inner):
        monkeypatch.setattr(m, "ON_DEATH", table)


def test_only_a_unit_with_the_key_gets_the_tag(monkeypatch):
    keys(monkeypatch, {"TEST_RIDER": "MILITIA"})
    assert combat.on_death_command("u-1", "TEST_RIDER") == "tag u-1 add aoe2mc.on_death"
    assert combat.on_death_command("u-1", "ARCHER") is None


def test_a_summoned_unit_with_the_key_gets_the_tag(monkeypatch):
    keys(monkeypatch, {"SCOUT_CAVALRY": "MILITIA"})
    server, g = setup()
    u = train.summon(g, "SCOUT_CAVALRY", (10.5, 64.0, 10.5))
    v = train.summon(g, "ARCHER", (11.5, 64.0, 10.5))
    assert f"tag {u} add aoe2mc.on_death" in server.log and f"tag {v} add aoe2mc.on_death" not in server.log


def test_the_new_unit_rises_at_the_marker_after_the_wait_for_free(monkeypatch):
    keys(monkeypatch, {"SCOUT_CAVALRY": "MILITIA"})
    server, g = setup()
    del server.entities["l"]                                           # the scout cavalry dies ...
    server.entities[MARKER] = {"Pos": (20.5, 64.0, 7.5)}               # ... and the plugin marks its place
    stock, before = dict(g.stock), dict(g.soldiers)
    train.census(g)
    assert "l" not in g.soldiers and "kill @e[type=marker,tag=aoe2mc.fell.l]" in server.log
    wait = train.RISE - train.CENSUS / 2
    train.risen(g, wait - 0.1)
    assert g.soldiers.keys() == before.keys() - {"l"}
    train.risen(g, 0.2)
    new = {u: n for u, n in g.soldiers.items() if u not in before}
    (u, name), = new.items()
    assert name == "MILITIA" and server.entities[u]["Pos"] == (20.5, 64.0, 7.5) and g.stock == stock
    assert f"tag {u} add aoe2mc.on_death" not in server.log            # the new unit has no key
    train.risen(g, 10)
    assert len(g.soldiers) == len(before)                              # it rises once


def test_a_removed_or_live_unit_gives_no_new_unit(monkeypatch):
    keys(monkeypatch, {"SCOUT_CAVALRY": "MILITIA", "ARCHER": "MILITIA"})
    server, g = setup()
    del server.entities["l"]                                           # removed with no death: no marker
    train.census(g)                                                    # "c" lives on (a conversion keeps it)
    train.risen(g, 10)
    assert "MILITIA" not in g.soldiers.values() and "c" in g.soldiers


def test_a_save_keeps_the_wait_of_a_new_unit(monkeypatch):
    keys(monkeypatch, {"SCOUT_CAVALRY": "MILITIA"})
    server, g = setup()
    del server.entities["l"]
    server.entities[MARKER] = {"Pos": (20.5, 64.0, 7.5)}
    train.census(g)
    train.risen(g, 1.0)
    h = gather.Gather(server, g.data).setup()
    savegame.load(h, json.loads(json.dumps(savegame.dump(g))))
    assert h.risers == g.risers
    before = set(h.soldiers)
    train.risen(h, train.RISE)
    assert [h.soldiers[u] for u in set(h.soldiers) - before] == ["MILITIA"]


@pytest.mark.mc
def test_a_killed_unit_with_the_tag_leaves_a_marker_at_its_place(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, tagged, other = 200, "00000001-0000-0002-0000-000300000004", "00000005-0000-0006-0000-000700000008"
    with run.Game(world) as game:
        game.command("forceload add 0 0 16 16")
        game.command(f"fill 0 {y - 1} 0 15 {y - 1} 15 stone_bricks")
        game.command(f"summon zombie 4.5 {y} 6.5 {{NoAI:1b,UUID:[I;1,2,3,4]}}")
        game.command(f"summon zombie 9.5 {y} 6.5 {{NoAI:1b,UUID:[I;5,6,7,8]}}")
        game.command(f"tag {tagged} add aoe2mc.on_death")             # combat.on_death_command
        game.command(f"kill {tagged}")
        game.command(f"kill {other}")
        time.sleep(1.0)
        out = game.command(f"data get entity @e[type=marker,tag=aoe2mc.fell.{tagged},limit=1] Pos")
        assert "4.5d" in out and f"{y}.0d" in out and "6.5d" in out, out
        assert "Test failed" in game.command(f"execute if entity @e[type=marker,tag=aoe2mc.fell.{other}]")
