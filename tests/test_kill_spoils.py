"""Resources for kills and deaths (#2271, AoE2 DE): a fallen Tupi unit gives a part of its cost back (civs.FALLEN; not a
ship or a siege weapon), a Mapuche mounted unit gets gold for each military unit that it kills (civs.KILL_GOLD, the
score of the plugin), and the Danes loot a part of the cost of an enemy building that falls (civs.LOOT; not a wall or a
gate). Fake server of test_gather."""
import shutil
import time

import pytest
from test_mounted_attack import KNIGHT, floor
from test_ranged import data
from test_train_population import setup

from game import build, civs, combat, run, spoils, train


def game(civ):
    server, g = setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.stock = {r: 0 for r in g.stock}
    return server, g


def test_a_fallen_tupi_unit_gives_a_part_of_its_cost_back():
    server, g = game("TUPI")
    for u, name in (("m", "MILITIA"), ("r", "BATTERING_RAM"), ("s", "GALLEY")):
        g.soldiers[u] = name
        server.entities[u] = {"Pos": (8.5, 64.0, 8.5)}
    train.census(g)
    assert set(g.stock.values()) == {0}                                # all alive
    for u in ("m", "r", "s"):
        del server.entities[u]                                         # killed: no position
    train.census(g)
    train.census(g)                                                    # a dead unit gives its part only once
    cost, part = train.price(g, "MILITIA"), civs.FALLEN["TUPI"]
    assert g.stock["food"] == int(cost["food"] * part) and g.stock["gold"] == int(cost["gold"] * part)
    assert g.stock["wood"] == 0                                        # nothing for the ram and the galley


def test_a_fallen_unit_of_another_civilization_gives_nothing():
    server, g = game("BRITONS")
    g.soldiers["m"] = "MILITIA"
    train.census(g)
    assert set(g.stock.values()) == {0}


def test_a_mapuche_side_gets_gold_for_each_new_kill_of_the_plugin():
    server, g = game("MAPUCHE")
    gold = civs.KILL_GOLD["MAPUCHE"]
    kills = {"n": 0}
    command = server.command
    server.command = lambda c: (f"p1 has {kills['n']} [{spoils.OBJECTIVE}]"
                                if c == f"scoreboard players get p1 {spoils.OBJECTIVE}" else command(c))
    kills["n"] = 1                                                     # a knight kills a militia
    train.census(g)
    assert g.stock["gold"] == gold
    train.census(g)
    assert g.stock["gold"] == gold                                     # no new kill
    kills["n"] = 3
    train.census(g)
    assert g.stock["gold"] == 3 * gold
    server, g = game("BRITONS")
    train.census(g)
    assert f"scoreboard players get p1 {spoils.OBJECTIVE}" not in server.log  # no command for another civilization


def test_the_danes_loot_a_part_of_a_fallen_enemy_house_and_nothing_of_a_wall():
    for civ, wood in (("DANES", int(build.COSTS["HOUSE"]["wood"] * civs.LOOT["DANES"])), ("BRITONS", 0)):
        server, g = game(civ)
        house, wall = combat.target_uuid([19, 19, 21, 21]), "w"
        g.fort_names[wall], g.forts[wall] = "STONE_WALL", (0, 64, 0, 0, 104, 0)
        g.sieged |= {house, wall}                                      # both are targets of attack orders
        g.fall()                                                       # the plugin removed both targets
        assert g.fort_names[house] == "HOUSE" and g.stock["wood"] == wood and g.stock["stone"] == 0, civ


@pytest.mark.mc
def test_the_plugin_counts_the_kills_of_military_units_by_mounted_units(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    get = f"scoreboard players get p1 {spoils.OBJECTIVE}"
    with run.Game(world) as game:
        floor(game, x0, y, z0, 20)
        game.command(KNIGHT.format(x=x0 + 0.5, y=y, z=z0 + 2.5))
        game.command("team join p1 @e[tag=k]")
        game.command(combat.stats_command("@e[tag=k,limit=1]", "KNIGHT"))
        for tag, name in (("v", "VILLAGER"), ("m", "MILITIA")):
            game.command(f'summon zombie {x0 + 6.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name))
            assert game.command(f"aoe attack @e[tag=k] @e[tag={tag},limit=1]").strip() == "Attack: 1 units"
            end = time.time() + 20
            while time.time() < end and data(game, tag, "Health") is not None:
                time.sleep(0.1)
            assert data(game, tag, "Health") is None, f"the {name} is alive"
            assert ("has 1 " in game.command(get)) == (name == "MILITIA"), name   # no point for a villager
