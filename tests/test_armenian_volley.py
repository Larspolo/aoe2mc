"""The Armenian galleys and dromons fire one more projectile (#2379, AoE2 DE wiki "Armenians": "The Galley line and
Dromons fire one additional projectile each, which deal 1 attack and advertised attack, respectively"): the key
"volley", train.volley_command and `aoe volley` of the plugin. Fake server, and a fight on a server."""
import re
import shutil
import time

import pytest
from test_dock_train import dock_map

from game import civs, combat, run, train


def summoned(civ, name):
    """The commands of a new own unit name of a player of civilization civ."""
    server, g = dock_map()
    g.data["players"]["1"]["civ"] = civ
    del server.log[:]
    uuid = train.summon(g, name, (20.5, 63.0, 12.5))
    return uuid, server.log


def test_each_armenian_unit_of_the_key_volley_fires_a_second_projectile():
    for name, attack in civs.value("volley", "ARMENIANS", {}).items():
        uuid, log = summoned("ARMENIANS", name)
        assert f"aoe volley {uuid} 1 {attack}" in log and any(c.startswith(f"aoe range {uuid} ") for c in log), name


def test_a_frank_galley_and_an_armenian_fire_galley_fire_one_projectile():
    for civ, name in (("FRANKS", "GALLEY"), ("ARMENIANS", "FIRE_GALLEY")):
        uuid, log = summoned(civ, name)
        assert not any(c.startswith("aoe volley") for c in log), (civ, name)


@pytest.mark.mc
def test_an_armenian_galley_hits_with_two_arrows_on_a_server(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a pool in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 26 26")
        game.command(f"fill 0 {y - 1} 0 23 {y} 23 stone_bricks")
        game.command(f"fill 2 {y} 2 21 {y} 21 water")
        ids = {}
        for tag, x in (("a", 4.5), ("bb", 16.5)):   # own UUIDs: tags of other lengths
            assert "Summoned" in summon(game, "GALLEY", x, y + 0.5, 10.5, tag)
            ints = [int(i) for i in re.findall(r"-?\d+", game.command(
                f"data get entity @e[type=oak_boat,tag={tag},limit=1] UUID").rsplit(":", 1)[-1])]
            h = "".join(f"{i & 0xFFFFFFFF:08x}" for i in ints)
            ids[tag] = f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], "GALLEY"))     # the crew
        assert "Range: 1 units" in game.command(combat.range_command(ids["a"], "GALLEY", 4))
        assert "Volley: 1 units" in game.command(f"aoe volley {ids['a']} 1 1")
        game.command("team add red")
        game.command("team join red @e[tag=a]")
        game.command(f"execute as {ids['a']} on passengers run team join red @s")
        assert "Attack: 1 units" in game.command(f"aoe attack {ids['a']} {ids['bb']}")   # 12 blocks: in its 20
        hp = []
        for _ in range(60):
            time.sleep(0.25)
            out = game.command(f"execute as {ids['bb']} on passengers run data get entity @s Health")
            if not (m := re.findall(r"(\d+\.?\d*)f", out)):
                break
            hp.append(float(m[0]))
            if len(set(hp)) >= 4:
                break
        drops = [round(a - b) for a, b in zip(hp, hp[1:]) if a != b]
        shot = combat.damage("GALLEY", "GALLEY")                      # one shot, and the damage of the extra arrow
        assert drops and any(d % shot for d in drops), hp
