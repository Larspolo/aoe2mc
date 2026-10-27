"""The view of one player in the live replay (#1302): the enemy units out of its sight are hidden for the spectators
(plugin `aoe hide`, Paper Player#hideEntity). Fake RCON; the server test needs a real client."""
import os
import shutil
import sys
import time
import types

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import replay  # noqa: E402
from test_replay import Fake, data  # noqa: E402
from test_replay_walk import VIL  # noqa: E402

ENEMY = dict(VIL, uuid="u2", ref=11, player=2, tile=[12.5, 10.5])     # 10 tiles east of the villager (sight 4)


def play(timeline, pov=1, teams=None):
    d = data(timeline)
    d["objects"] += [VIL, ENEMY]
    for p, t in (teams or {}).items():
        d["players"][p]["team"] = t
    now, game = [0.0], Fake()

    def sleep(s):
        now[0] += s
    r = replay.Replay(game, d)
    r.pov = pov
    r.run(clock=lambda: now[0], sleep=sleep, log=None, finish=True)
    return [c for c in game.sent if c.startswith(("aoe hide", "aoe show"))]


def test_an_enemy_out_of_sight_is_hidden_and_shows_when_a_unit_comes_near():
    walk = [dict(time=1000, player=1, kind="move", objects=[7], tile=[10.5, 10.5])]
    assert play(walk) == ["aoe hide @a u2", "aoe show @a u2"]          # each change once, not each second
    assert play([dict(time=5000, player=1, kind="chat", text="hi")]) == ["aoe hide @a u2"]


def test_no_view_player_or_an_ally_hides_nothing():
    assert play([dict(time=5000, player=1, kind="chat", text="hi")], pov=None) == []
    assert play([dict(time=5000, player=1, kind="chat", text="hi")], teams={"1": 1, "2": 1}) == []


def test_the_view_of_player_2_hides_the_villager_of_player_1():
    assert play([dict(time=5000, player=1, kind="chat", text="hi")], pov=2) == ["aoe hide @a u1"]


def test_many_units_go_into_few_commands_below_the_rcon_limit():
    r = replay.Replay(Fake(), data([]))
    r.pov = 1
    r.units = {i: types.SimpleNamespace(uuid=f"{i:08d}-0000-0000-0000-000000000000", player=2, name="MILITIA",
                                        pos=(60.0, 70.0, 60.0)) for i in range(100)}
    cmds = r.fog()
    assert len(cmds) == 3 and all(len(c) <= replay.RCON_MAX for c in cmds)
    assert sum(len(c.split()) - 3 for c in cmds) == 100 and r.fog() == []


@pytest.mark.mc
def test_a_hidden_entity_is_not_in_the_view_of_the_player(tiny_world, tmp_path):
    import mc_shot
    from test_mc_check import mojang_reachable
    from test_paper import paper_reachable
    if not all(shutil.which(t) for t in ("Xvfb", "import")) or not mojang_reachable() or not paper_reachable():
        pytest.skip("Xvfb, Mojang or Paper is not available")
    from game import run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game, mc_shot.Client(game.game_port, game.version) as client:
        client.wait_join(lambda: "aoe2mc" in game.command("list").split(":", 1)[-1])
        uuid = "00000000-0000-0000-0000-000000000516"                         # 1302 = 0x516
        game.command('execute at aoe2mc run summon cow ~3 ~ ~ {UUID:[I;0,0,0,1302],NoAI:1b}')
        assert game.command(f"aoe sees aoe2mc {uuid}").strip() == "Sees: 1"
        assert game.command(f"aoe hide @a {uuid}").strip() == "Hidden: 1 entities, 1 players"
        time.sleep(1)
        assert game.command(f"aoe sees aoe2mc {uuid}").strip() == "Sees: 0"
        assert game.command(f"aoe show @a {uuid}").strip() == "Shown: 1 entities, 1 players"
        assert game.command(f"aoe sees aoe2mc {uuid}").strip() == "Sees: 1"
