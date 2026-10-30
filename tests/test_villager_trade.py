"""A villager unit has no trades: a right click near it selects it and opens no trade menu (#988)."""
import shutil
import time

import pytest

import units
from game import gather


def test_each_villager_unit_has_an_empty_trade_list():
    for name in ("VILLAGER_MALE", "VILLAGER_FEMALE", "VILLAGER_MALE_LUMBERJACK", "VILLAGER_FEMALE_FARMER", "REPAIRER"):
        d = units.classify(name, False)
        assert d["id"] == "minecraft:villager" and d["Offers"] == {"Recipes": []}, name


def test_no_mob_of_a_unit_or_hero_can_trade():
    from AoE2ScenarioParser.datasets.heroes import HeroInfo
    from AoE2ScenarioParser.datasets.units import UnitInfo
    names = [(u.name, False) for u in UnitInfo] + [(h.name, True) for h in HeroInfo]
    for name, hero in names:
        top = units.classify(name, hero) or {}                         # None: no entity (an invisible unit)
        for d in (top, *top.get("Passengers", ())):
            assert d.get("id") not in ("minecraft:villager", "minecraft:wandering_trader") \
                or d.get("Offers") == {"Recipes": []}, name


def test_a_new_profession_keeps_the_trade_list_empty():
    assert gather.profession("v", "farmer") == \
        'data merge entity v {VillagerData:{profession:"minecraft:farmer"},Offers:{Recipes:[]}}'


@pytest.mark.mc
def test_a_right_click_near_a_villager_counts_and_opens_no_trades(tiny_world, tmp_path):
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import", "xdotool")) or not mojang_reachable() \
            or not paper_reachable():
        pytest.skip("Xvfb, xdotool, Mojang or Paper is not available")
    import mc_shot

    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        time.sleep(5)                                                  # the world is drawn
        for c in ("gamemode adventure aoe2mc", "scoreboard objectives add aoe_talk "
                  "minecraft.custom:minecraft.talked_to_villager", "forceload add 0 0",
                  "fill -2 99 -2 2 99 4 stone", "fill -2 100 -2 2 103 4 air",
                  "tp aoe2mc 0.5 100 0.5 0 15",                       # look south (+z), a little down
                  'summon villager 0.5 100 2.5 {NoAI:1b,Tags:["t988"],Offers:{Recipes:[]},'
                  'VillagerData:{profession:"minecraft:farmer",level:2,type:"minecraft:plains"}}'):
            game.command(c)
        time.sleep(3)
        for job in (None, "fletcher"):
            if job:
                game.command(gather.profession("@e[tag=t988,limit=1]", job))
                time.sleep(1)
            client.click(client.size[0] // 2, client.size[1] // 2, button=3)
            time.sleep(2)
            recipes = game.command("data get entity @e[tag=t988,limit=1] Offers.Recipes")
            assert "Found no elements" in recipes or recipes.strip().endswith("[]"), recipes   # no trades: no menu
        talks = game.command("scoreboard players get aoe2mc aoe_talk")
        assert "has 2 " in talks, talks                               # the game program sees both clicks
        game.command("kill @e[tag=t988]")                             # the control: a villager without Offers
        game.command('summon villager 0.5 100 2.5 {NoAI:1b,Tags:["c988"],'
                     'VillagerData:{profession:"minecraft:farmer",level:2,type:"minecraft:plains"}}')
        time.sleep(2)
        client.click(client.size[0] // 2, client.size[1] // 2, button=3)
        time.sleep(2)
        client.shot(str(tmp_path / "control.png"))
        recipes = game.command("data get entity @e[tag=c988,limit=1] Offers.Recipes")
        assert "Found no elements" not in recipes and not recipes.strip().endswith("[]"), recipes  # it trades
