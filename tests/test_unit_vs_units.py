"""A unit with two attack modes (#4505, the Lou Chuan): the key "vs_units" of data/units.jsonl gives the pierce attack,
range and bonus at a target that is not a building; a building takes the values of the line. Test data."""
import shutil
import time

import combat as plain
import pytest
from test_building_damage import hp as house
from test_ranged import data

from game import combat, run

MODE = {"attack": 5, "range": 10, "bonus": {"ship": 5}}


def mode(monkeypatch, vs=MODE):
    for m in (combat, plain):                                          # train imports the plain name
        monkeypatch.setattr(m, "VS_UNITS", {"TREBUCHET": vs})


def test_a_unit_takes_the_anti_unit_damage(monkeypatch):
    mode(monkeypatch)
    t = combat.stats("GALLEY")
    want = max(1, MODE["attack"] - t.pierce + sum(MODE["bonus"].get(c, 0) for c in t.classes))
    assert combat.damage("TREBUCHET", "GALLEY") == want
    assert combat.damage("TREBUCHET", "MILITIA") == max(1, MODE["attack"] - combat.stats("MILITIA").pierce)


def test_a_building_takes_the_values_of_the_line(monkeypatch):
    building = combat.stats("TREBUCHET")._replace(classes=("building",), bonus={})   # a target of class building
    before = combat.damage("TREBUCHET", "X", t=building)
    mode(monkeypatch)
    assert combat.damage("TREBUCHET", "X", t=building) == before


def test_the_command_holds_the_mode(monkeypatch):
    mode(monkeypatch)
    assert combat.vs_units_command("u", "TREBUCHET", 4) == "aoe vsunits u 5 ship:5 40"
    assert combat.vs_units_command("u", "MILITIA", 4) is None
    mode(monkeypatch, {"attack": 3, "range": 2})
    assert combat.vs_units_command("u", "TREBUCHET", 4) == "aoe vsunits u 3 - 8"


@pytest.mark.mc
def test_the_plugin_hurts_a_unit_in_the_anti_unit_mode_and_a_building_with_the_line(tiny_world, tmp_path, monkeypatch):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    for m in (combat, plain):
        monkeypatch.setattr(m, "VS_UNITS", {"CHAMPION": MODE})
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y, box = 200, (8, 200, 8, 13, 240, 13)                             # a house in the air, inside the world border
    with run.Game(world) as game:
        game.command("forceload add -2 -2 24 24")
        game.command("time set midnight")                              # no sun: a zombie burns by day
        game.command(f"fill 0 {y - 1} 0 21 {y - 1} 21 stone_bricks")
        game.command(f"fill 8 {y} 8 13 {y + 3} 13 oak_planks")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        uuid = combat.target_uuid([8, 8, 14, 14])
        for c in combat.building(uuid, "HOUSE", 2, box):
            game.command(c)
        for tag, x, team, name in (("a", 4.5, "p1", "CHAMPION"), ("b", 17.5, "p1", "CHAMPION"), ("m", 6.5, "p2", "MILITIA")):
            game.command(f'summon zombie {x} {y} 4.5 {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name))
        for tag in ("a", "b"):
            assert game.command(combat.vs_units_command(f"@e[tag={tag},limit=1]", "CHAMPION", 4)).strip() == "Vsunits: 1 units"
        full, hp = combat.stats("MILITIA").hp, combat.stats("HOUSE").hp
        assert game.command("aoe attack @e[tag=a] @e[tag=m,limit=1]").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and (data(game, "m", "Health") or [full])[0] >= full:
            time.sleep(0.1)
        assert full - data(game, "m", "Health")[0] == combat.damage("CHAMPION", "MILITIA")   # 5 pierce attack, not 13
        assert game.command(f"aoe attack @e[tag=b] {uuid}").strip() == "Attack: 1 units"
        end = time.time() + 20
        while time.time() < end and house(game, uuid) == hp:
            time.sleep(0.1)
        assert hp - house(game, uuid) == combat.damage("CHAMPION", "HOUSE")         # the values of the line
