"""game/cheats.py: "torpedo<n>" also removes the queues, the construction sites and the bot of player n (#1657)."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
from test_cheat_end import cheat, game  # noqa: E402

from game import bot, cheats, gather  # noqa: E402


def site(player, footprint, done=False):
    return {"name": "MILL", "player": player, "footprint": footprint, "commands": [], "sent": 0,
            "progress": 1.0 if done else 0.3, "ring": {}, "under": {}, "done": done}


def setup():
    server, g = game()
    b = bot.Bot(server, g.data, player=2, share=g).setup()
    g.bots = [b]
    b.g.sites += [site(2, (4, 6, 14, 16)), site(2, (8, 10, 14, 16), done=True)]   # the sites of a bot: its own Gather
    b.g.map.blocked |= {(x, z) for x in range(4, 10) for z in range(14, 16)}
    b.g.queues[(10, 12, 10, 12)] = [{"name": "VILLAGER_MALE", "player": 2, "progress": 0.5}]
    g.sites.append(site(1, (0, 2, 14, 16)))
    return server, g, b


def test_torpedo_removes_the_sites_of_a_bot():
    server, g, b = setup()
    log = cheat(server, g, "torpedo2")
    assert "fill 4 64 14 5 104 15 minecraft:air" in log and "fill 8 64 14 9 104 15 minecraft:air" in log
    assert b.g.sites == [] and not b.g.map.blocked & {(4, 14), (9, 15)}
    assert [s["player"] for s in g.sites] == [1]                   # the own site stays
    assert not any(c.startswith("fill 0 ") for c in log)


def test_torpedo_empties_the_queues_and_stops_the_bot():
    server, g, b = setup()
    cheat(server, g, "torpedo2")
    assert b.g.queues == {} and g.bots == []                       # Gather.run steps no bot: no unit of player 2 spawns


def test_torpedo_of_another_player_keeps_the_bot():
    server, g, b = setup()
    cheat(server, g, "torpedo3")
    assert g.bots == [b] and len(b.g.sites) == 2 and b.g.queues


@pytest.mark.mc
def test_torpedo_removes_a_bot_with_its_sites_on_a_server(tmp_path):
    """The owner check of #1138: the unfinished mill of the bot stayed, and its queue spawned new villagers."""
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json

    import scenarios

    import aoe2mc
    from game import build, combat, conquest, run
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.four_civs(str(tmp_path / "s.aoe2scenario")), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, cheats=True).setup()
        b = bot.Bot(game, data, player=2, share=g, start={}).setup()
        g.bots = [b]
        T = b.g.map.T
        home = next(o for o in data["objects"] if o["kind"] == "building" and o["player"] == 2)
        cells = [(home["footprint"][0] + dx * T, home["footprint"][1] + dz * T) for dx in range(-8, 9) for dz in range(-8, 9)]
        rects = [r for c in cells if build.free(b.g, r := build.area(b.g, "MILL", c))]
        mill = build.found(b.g, "MILL", rects[0])                     # a foundation: the wool ring, no target
        build.rise(b.g, mill, 1.0)
        x0, x1, z0, z1 = mill["footprint"]
        y = b.g.map.y(x0, z0)
        assert "passed" in game.command(f"execute if block {x0} {y} {z0} #minecraft:wool")
        b.g.queues[tuple(home["footprint"])] = [{"name": "VILLAGER_MALE", "player": 2, "progress": 0.9}]
        game.command("team join p2 @e[tag=aoe2mc.p2,team=]")           # the pulse of the datapack, at once
        conquest.tick(g)                                               # player 2 is in the game
        assert 2 in g.conquest_seen and not g.ended
        cheats.apply(g, "aoe2mc", "torpedo2")
        g.run(seconds=4)                                               # a dead mob stays 20 ticks; the bot no longer steps
        assert "passed" in game.command(f"execute if block {x0} {y} {z0} minecraft:air")
        assert not conquest.alive(g, 2) and b.g.queues == {} and g.bots == []
        assert 2 in g.defeated and not g.ended                        # conquest.tick; players 3 and 4 are left
