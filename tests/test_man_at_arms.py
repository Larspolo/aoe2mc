"""game/train.py: the barracks has the Man-at-Arms upgrade in the Feudal Age (a book, 100 food and 40 gold, 40 AoE2
seconds). After the research the live militia of the player are men-at-arms (name and values), and the barracks trains
men-at-arms instead of militia, as in AoE2 (#941)."""
import contextlib
import io
import json

import pytest
from test_forging import menus, setup

from game import combat, gather, run, train

BARRACKS = (17, 3)


def feudal(food=100, gold=40):
    server, g = setup(food=food)
    g.stock.update(gold=gold)
    g.techs.add("FEUDAL_AGE")
    return server, g


def research(g):
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.order(g, "Steve", rect, 2) == 1
    train.tick(g, train.TRAIN_TIMES["MAN_AT_ARMS_UPGRADE"])
    return rect


def test_no_upgrade_in_the_dark_age():
    server, g = setup(food=100, age=0)
    g.stock.update(gold=40)
    train.open_menu(g, "Steve", BARRACKS)
    assert "Man-at-Arms" not in menus(server)[-1]
    assert train.queue(g, "Steve", BARRACKS, "MAN_AT_ARMS_UPGRADE") is None


def test_the_barracks_menu_has_the_upgrade_in_the_feudal_age():
    server, g = feudal()
    train.open_menu(g, "Steve", BARRACKS)
    assert " 2:book:Man-at-Arms:100 food · 40 gold · 40 s · research " in menus(server)[-1] + " "


def test_the_live_militia_becomes_a_man_at_arms():
    server, g = feudal()
    research(g)
    assert "MAN_AT_ARMS_UPGRADE" in g.techs and g.soldiers["m"] == "MAN_AT_ARMS"
    assert g.soldiers["s"] == "SCOUT_CAVALRY" and g.soldiers["a"] == "ARCHER"           # other units stay
    assert combat.stats_command("m", "MAN_AT_ARMS", train.stats(g, "MAN_AT_ARMS")) in server.log
    assert "aoe label m Man At Arms" in server.log
    assert combat.stats("MAN_AT_ARMS").hp == 45 and combat.stats("MAN_AT_ARMS").attack == 6
    assert any("Man-at-Arms is researched." in c for c in server.log if c.startswith("tellraw"))


def test_the_barracks_trains_men_at_arms_after_the_upgrade():
    server, g = feudal(food=160, gold=60)
    rect = research(g)
    train.open_menu(g, "Steve", BARRACKS)
    menu = menus(server)[-1]
    assert " 0:zombie_spawn_egg:Man-at-Arms:60 food · 20 gold · 21 s · queue " in menu
    assert "Militia" not in menu and ":book:Man-at-Arms" not in menu                     # the upgrade only once
    assert train.queue(g, "Steve", BARRACKS, "MILITIA") is None
    assert train.queue(g, "Steve", BARRACKS, "MAN_AT_ARMS") == rect
    uuid, = train.tick(g, train.TRAIN_TIMES["MAN_AT_ARMS"])
    assert g.soldiers[uuid] == "MAN_AT_ARMS"
    assert combat.stats_command(uuid, "MAN_AT_ARMS", train.stats(g, "MAN_AT_ARMS")) in server.log


@pytest.mark.mc
def test_a_live_militia_gets_the_name_and_values_on_a_server(tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not mojang_reachable() or not paper_reachable():
        pytest.skip("Mojang or Paper is not reachable")
    import aoe2mc
    import scenarios
    from AoE2ScenarioParser.datasets.buildings import BuildingInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    scn = scenarios.new_scenario(16)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, BuildingInfo.BARRACKS.ID, x=4.5, y=4.5)
    scn.unit_manager.add_unit(scenarios.PlayerId.ONE, UnitInfo.MILITIA.ID, x=10.5, y=10.5)
    src = str(tmp_path / "militia.aoe2scenario")
    scenarios.save(scn, src)
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(src, str(tmp_path / "W"))
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        data = json.load(f)
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        g = gather.Gather(game, data, tick=0.25, start={}).setup()
        uuid, = [u for u, n in g.soldiers.items() if n == "MILITIA"]
        g.techs.add("FEUDAL_AGE")
        g.stock.update(food=100, gold=40)
        rect, = train.homes(g)
        assert train.queue(g, "nobody", rect[::2], "MAN_AT_ARMS_UPGRADE")
        train.tick(g, train.TRAIN_TIMES["MAN_AT_ARMS_UPGRADE"])
        assert g.soldiers[uuid] == "MAN_AT_ARMS"
        hp = game.command(f"attribute {uuid} minecraft:max_health get")
        assert hp.rstrip().endswith(" 45.0") or " 45" in hp, hp                 # AoE2: 45 hit points
        game.command(f"aoe label {uuid}")
        name = game.command(f"data get entity {uuid} CustomName")
        assert "Man At Arms" in name and "Militia" not in name, name
        assert '"color"' in name or "color:" in name, name                      # the player color stays
