"""The camel rider (#1550): the stable trains it in the Castle Age (55 food, 60 gold, 22 s; AoE2 DE wiki infobox
"Camel Rider") and researches Heavy Camel Rider in the Imperial Age (325 food, 360 gold, 105 s: its UpCost and UpTime).
Only the civilizations with the unit in the wiki chart see it."""
import json
import shutil

import pytest
from test_castle_upgrades import STABLE, research, setup
from test_forging import menus
from test_mounted_attack import floor, hits

from game import civs, combat, gather, run, train

CASTLE = ("FEUDAL_AGE", "CASTLE_AGE")


def stable(civ="TURKS", ages=CASTLE + ("IMPERIAL_AGE",)):   # no camel bonus (Byzantines: -25 % cost)
    server, g = setup(ages=ages)
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["cr"] = "CAMEL_RIDER"
    g.game.entities.setdefault("cr", {"Pos": (0.5, 64.0, 0.5)})          # alive at the census (#3122)
    return server, g


def test_the_values_are_those_of_aoe2():
    assert all(len(train.HELP[n]) <= 50 for n in ("CAMEL_RIDER", "HEAVY_CAMEL_RIDER", "HEAVY_CAMEL_RIDER_UPGRADE"))
    assert {"FRANKS", "CHINESE", "AZTECS"} <= set(civs.MISSING["CAMEL_RIDER"])
    assert not {"BYZANTINES", "SARACENS", "CUMANS", "HINDUSTANIS"} & set(civs.MISSING["CAMEL_RIDER"])
    assert "CUMANS" in civs.MISSING["HEAVY_CAMEL_RIDER_UPGRADE"]
    assert not {"BYZANTINES", "SARACENS", "TURKS"} & set(civs.MISSING["HEAVY_CAMEL_RIDER_UPGRADE"])


def test_the_camel_rider_is_in_the_stable_menu_in_the_castle_age_and_the_upgrade_in_the_imperial_age():
    server, g = stable(ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", STABLE)
    assert "6:gray_dye:Camel Rider:55 food · 60 gold · 22 s · Needs the Castle Age" in menus(server)[-1]
    server, g = stable(ages=CASTLE)
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert "6:camel_spawn_egg:Camel Rider:55 food · 60 gold · 22 s · queue" in menu and "Heavy Camel" not in menu
    g.techs.add("IMPERIAL_AGE")
    train.open_menu(g, "Steve", STABLE)
    assert f"{train.MORE}:book:Heavy Camel Rider:325 food · 360 gold · 105 s · research" in menus(server)[-1]


def test_the_live_camel_riders_become_heavy_and_the_stable_trains_them():
    server, g = stable()
    research(g, STABLE, "HEAVY_CAMEL_RIDER_UPGRADE")
    assert g.soldiers["cr"] == "HEAVY_CAMEL_RIDER"
    assert combat.stats_command("cr", "HEAVY_CAMEL_RIDER") in server.log
    train.open_menu(g, "Steve", STABLE)
    menu = menus(server)[-1]
    assert "6:camel_spawn_egg:Heavy Camel Rider:55 food · 60 gold · 22 s · queue" in menu and ":Camel Rider:" not in menu
    assert train.queue(g, "Steve", STABLE, "HEAVY_CAMEL_RIDER")


def test_a_civilization_without_camels_does_not_see_them():
    server, g = stable("FRANKS")
    train.open_menu(g, "Steve", STABLE)
    assert "Camel" not in menus(server)[-1]
    server, g = stable("CUMANS")                                       # the camel rider, not the heavy one
    train.open_menu(g, "Steve", STABLE)
    assert ":Camel Rider:" in menus(server)[-1] and "Heavy Camel" not in menus(server)[-1]


@pytest.mark.mc
def test_a_trained_camel_rider_rides_a_camel_and_attacks(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        g = gather.Gather(game, json.loads((world / "aoe2mc.json").read_text())).setup()
        uuid = train.summon(g, "CAMEL_RIDER", (x0 + 0.5, y, z0 + 2.5))
        assert g.soldiers[uuid] == "CAMEL_RIDER"
        assert game.command("execute if entity @e[type=camel,nbt={Passengers:[{id:\"minecraft:zombie\"}]}]") \
            .strip().endswith("1")                                     # a rider on a camel
        game.command(f'summon villager {x0 + 12.5} {y} {z0 + 2.5} {{NoAI:1b,Tags:["v"]}}')
        game.command("team join p2 @e[tag=v]")
        game.command(combat.stats_command("@e[tag=v,limit=1]", "VILLAGER"))
        assert game.command(f"aoe attack {uuid} @e[tag=v,limit=1]").strip() == "Attack: 1 units"
        assert hits(game, "v", 25.0, 2, 30) == [19.0, 13.0]           # attack 6, villager armor 0
