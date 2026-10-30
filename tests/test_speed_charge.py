"""The speed charge of a unit (#4545, the Samurai): the key "speed_charge" of data/units.jsonl sends `aoe speedcharge`
for each new unit; the plugin makes the unit faster while its target is in the distance. Test data, fake server of
test_gather, and a Paper server."""
import shutil
import time

import combat as plain
import pytest
from test_kill_spoils import game
from test_low_hp import value

from game import combat, run, train

CHARGE = {"speed": 0.25, "min": 2, "max": 6}


def speed_charge(monkeypatch):
    for m in (combat, plain):                                          # train imports the plain name
        monkeypatch.setattr(m, "SPEED_CHARGE", {"MILITIA": CHARGE})


def test_a_new_unit_with_the_key_gets_its_speed_charge(monkeypatch):
    speed_charge(monkeypatch)
    server, g = game("FRANKS")
    u = train.summon(g, "MILITIA", (8.5, 64.0, 8.5))
    T = g.map.T
    assert f"aoe speedcharge {u} 0.25 {2 * T} {6 * T}" in server.log
    assert combat.speed_charge_command("u", "MILITIA", 4) == "aoe speedcharge u 0.25 8 24"


def test_a_unit_without_the_key_gets_none(monkeypatch):
    speed_charge(monkeypatch)
    server, g = game("FRANKS")
    train.summon(g, "SPEARMAN", (8.5, 64.0, 8.5))
    assert not any(c.startswith("aoe speedcharge") for c in server.log)
    assert combat.speed_charge_command("u", "SPEARMAN", 4) is None


@pytest.mark.mc
def test_the_unit_is_faster_only_while_its_target_is_in_the_distance(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    with run.Game(world) as game:
        game.command("forceload add 0 0 31 31")
        game.command(f"fill 0 {y - 1} 0 31 {y - 1} 31 stone_bricks")
        game.command("time set midnight")                 # a zombie burns in the sun
        game.command(f'summon zombie 4.5 {y} 4.5 {{NoAI:1b,IsBaby:0b,Tags:["s"]}}')
        game.command(f'summon zombie 20.5 {y} 4.5 {{NoAI:1b,IsBaby:0b,Tags:["t"]}}')
        game.command("aoe attack @e[tag=s,limit=1] @e[tag=t,limit=1]")
        assert game.command("aoe speedcharge @e[tag=s,limit=1] 0.25 8 24").strip() == "Speed charge: 1 units"

        def speed():
            time.sleep(0.5)
            return (value(game.command("attribute @e[tag=s,limit=1] minecraft:movement_speed get"))
                    / value(game.command("attribute @e[tag=s,limit=1] minecraft:movement_speed base get")))

        assert speed() == pytest.approx(1.25, abs=0.01)   # 16 blocks: in the distance
        game.command(f"tp @e[tag=t,limit=1] 5.5 {y} 4.5")
        assert speed() == pytest.approx(1)                # at the hit: the normal speed again
        game.command(f"tp @e[tag=t,limit=1] 30.5 {y} 4.5")
        assert speed() == pytest.approx(1)                # 26 blocks: too far
