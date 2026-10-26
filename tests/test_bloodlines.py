"""game/train.py: the stable menu has "Bloodlines" in the Feudal Age (a book, 150 food and 100 gold, 50 AoE2 seconds).
After the research the cavalry of the player has 20 more hit points, also the live units: they keep their lost hit
points, as in AoE2 (#940)."""
import shutil
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid

from game import combat, gather, run, train
from test_mounted_attack import floor
from test_ranged import data


def setup(feudal=True):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 at blocks x 2-4, z 2-4, a built stable at x 10-12,
    z 2-4, a militia and a scout."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m", "tile": [9.5, 9.5]},
               {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 1, "uuid": "s", "tile": [11.5, 11.5]}]
    server = FakeServer({u: {"Pos": (p, 64.0, p)} for u, p in (("m", 9.5), ("s", 11.5))})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.sites.append({"name": "STABLE", "player": 1, "footprint": [10, 13, 2, 5], "done": True})
    g.stock.update(food=150, gold=100)
    if feudal:
        g.techs.add("FEUDAL_AGE")
    return server, g


def menus(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")]


def test_bloodlines_is_hidden_in_the_dark_age():
    server, g = setup(feudal=False)
    train.open_menu(g, "Steve", (11, 3))
    assert "Bloodlines" not in menus(server)[-1]


def test_bloodlines_gives_cavalry_20_hit_points():
    server, g = setup()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert " 1:book:Bloodlines:150 food · 100 gold · 50 s · research " in menus(server)[-1] + " "
    assert train.order(g, "Steve", rect, 1) == 1 and g.stock["food"] == 0 and g.stock["gold"] == 0
    train.tick(g, 49)
    assert "BLOODLINES" not in g.techs
    train.tick(g, 1)
    assert "BLOODLINES" in g.techs
    assert train.stats(g, "SCOUT_CAVALRY").hp == combat.stats("SCOUT_CAVALRY").hp + 20 == 65
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")
    stats = [c for c in server.log if c.startswith("aoe stats")]
    assert stats == [combat.stats_command("s", "SCOUT_CAVALRY", train.stats(g, "SCOUT_CAVALRY"))]
    assert stats[0].startswith("aoe stats s 65 ")
    assert any("Bloodlines is researched." in c for c in server.log if c.startswith("tellraw"))
    assert train.queue(g, "Steve", rect, "BLOODLINES") is None             # only once


SCOUT = ('summon horse {x} {y} {z} {{NoAI:1b,Tame:1b,Tags:["b","b{i}"],'
         'equipment:{{saddle:{{id:"minecraft:saddle",count:1}}}},'
         'Passengers:[{{id:"minecraft:zombie",NoAI:1b,Tags:["br"]}}]}}')


@pytest.mark.mc
def test_a_live_scout_gets_20_hit_points(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    s = combat.stats("SCOUT_CAVALRY")
    with run.Game(world) as game:
        floor(game, 1, 200, 1, 4)
        for i in range(2):                                  # b0 has full health, b1 lost 15 hit points
            game.command(SCOUT.format(x=2 * i + 1.5, y=200, z=3.5, i=i))
            game.command(combat.stats_command(f"@e[tag=b{i},limit=1]", "SCOUT_CAVALRY"))
        game.command("data modify entity @e[tag=b1,limit=1] Health set value 30f")
        assert [data(game, f"b{i}", "Health") for i in range(2)] == [[45.0], [30.0]]
        for i in range(2):
            game.command(combat.stats_command(f"@e[tag=b{i},limit=1]", "SCOUT_CAVALRY", s._replace(hp=s.hp + 20)))
        assert [data(game, f"b{i}", "Health") for i in range(2)] == [[65.0], [50.0]]
        for i in range(2):
            assert "65" in game.command(f"attribute @e[tag=b{i},limit=1] minecraft:max_health get")
