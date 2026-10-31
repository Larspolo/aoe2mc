"""game/train.py: the stable menu has "Bloodlines" in the Feudal Age (a book). After the research the cavalry of the
player has more hit points, also the live units: they keep their lost hit
points, as in AoE2 (#940)."""
import shutil
from urllib.parse import unquote

import lang
import pytest
from menu_line import item
from test_gather import FakeServer, grid
from test_mounted_attack import floor
from test_ranged import data

from game import combat, gather, run, train


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


def test_bloodlines_gives_cavalry_hit_points():
    server, g = setup()
    cost, t = train.price(g, "BLOODLINES"), train.TRAIN_TIMES["BLOODLINES"]
    g.stock.update(cost)
    rect = train.open_menu(g, "Steve", (11, 3))
    line = item(menus(server)[-1], "Bloodlines")
    assert line.endswith(":Bloodlines:" + " · ".join(f"{v} {r}" for r, v in cost.items()) + f" · {t} s · research")
    assert train.order(g, "Steve", rect, int(line.split(":")[0])) == 1 and not any(g.stock[r] for r in cost)
    train.tick(g, t - 1)
    assert "BLOODLINES" not in g.techs
    train.tick(g, 1)
    assert "BLOODLINES" in g.techs
    hp = train.stats(g, "SCOUT_CAVALRY").hp
    assert hp > combat.stats("SCOUT_CAVALRY").hp
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")
    stats = [c for c in server.log if c.startswith("aoe stats")]
    assert stats == [combat.stats_command("s", "SCOUT_CAVALRY", train.stats(g, "SCOUT_CAVALRY"))]
    assert stats[0].startswith(f"aoe stats s {hp} ")
    assert any("Bloodlines is researched." in c for c in map(lang.english, server.log) if c.startswith("tellraw"))
    assert train.queue(g, "Steve", rect, "BLOODLINES") is None             # only once


SCOUT = ('summon horse {x} {y} {z} {{NoAI:1b,Tame:1b,Tags:["b","b{i}"],'
         'equipment:{{saddle:{{id:"minecraft:saddle",count:1}}}},'
         'Passengers:[{{id:"minecraft:zombie",NoAI:1b,Tags:["br"]}}]}}')


@pytest.mark.mc
def test_a_live_scout_gets_20_hit_points(tiny_world, tmp_path):
    """Test values: a scout of the data, 20 more hit points; one scout lost 15."""
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
        game.command(f"data modify entity @e[tag=b1,limit=1] Health set value {s.hp - 15}f")
        assert [data(game, f"b{i}", "Health") for i in range(2)] == [[float(s.hp)], [s.hp - 15.0]]
        for i in range(2):
            game.command(combat.stats_command(f"@e[tag=b{i},limit=1]", "SCOUT_CAVALRY", s._replace(hp=s.hp + 20)))
        assert [data(game, f"b{i}", "Health") for i in range(2)] == [[s.hp + 20.0], [s.hp + 5.0]]
        for i in range(2):
            assert str(s.hp + 20) in game.command(f"attribute @e[tag=b{i},limit=1] minecraft:max_health get")
