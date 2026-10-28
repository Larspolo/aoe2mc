"""`run.py --play --victory regicide` (#2357, AoE2 wiki "Regicide (game mode)"): each player with a town center gets a
King in front of it, and the death of the King of a player is its defeat, also with units and buildings left."""
import time

import pytest
from test_conquest import check, setup as conquest_setup
from test_garrison_game import Server
from test_gather import grid

from game import conquest, gather


def crowned():
    """A flat 24 × 24 map: the town centers of players 1 and 2 (player 3 has none), and the Kings of crown()."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 2, "tile": [15.5, 15.5], "footprint": [14, 14, 17, 17]},
               {"kind": "unit", "name": "MILITIA", "player": 3, "uuid": "m3", "tile": [20.5, 3.5]}]
    server = Server({"m3": {"Pos": (20.5, 64.0, 3.5)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects)).setup()
    g.players = g.data["players"] = {str(p): {"color": "blue"} for p in (0, 1, 2, 3)}
    bot = gather.Gather(server, g.data, player=2).setup()
    conquest.crown(g, [g, bot])
    return server, g, bot


def test_each_player_with_a_town_center_gets_a_king_in_front_of_it():
    server, g, bot = crowned()
    assert sorted(g.kings) == [1, 2]
    summons = [c for c in server.log if c.startswith("summon ") and "King" in c]
    assert len(summons) == 2
    x, _, z = map(float, summons[0].split()[2:5])
    assert 2 <= x < 5 and z == 5.5                                       # south of the town center of player 1
    assert g.soldiers[g.kings[1]] == "KING" and g.kings[2] not in g.soldiers   # the own King takes move orders
    assert bot.soldiers[g.kings[2]] == "KING"                            # the bot has its King


def kings(server, dead):
    """The fake server answers `execute if entity` of the Kings "k1" and "k2": the ones in dead are gone."""
    command = server.command
    server.command = lambda cmd: ("Test failed" if cmd.split()[-1] in dead else "Test passed") \
        if cmd.startswith("execute if entity k") else command(cmd)


def test_the_death_of_a_king_is_the_defeat_and_the_last_side_wins():
    server, g = conquest_setup()
    g.kings = {1: "k1", 2: "k2"}
    kings(server, set())
    check(g)
    assert not g.ended
    kings(server, {"k2"})                                                # player 2 has units and buildings left
    server.log.clear()
    check(g)
    assert g.defeated == {2} and g.ended == "Victory"
    assert 'tellraw @a {"text": "Player 2 is defeated.", "color": "red"}' in server.log


def test_the_death_of_the_own_king_is_the_defeat():
    server, g = conquest_setup()
    g.kings = {1: "k1", 2: "k2"}
    kings(server, {"k1"})
    check(g)
    assert g.ended == "Defeat"


@pytest.mark.mc
def test_the_kings_live_on_a_server_and_a_killed_king_is_the_defeat(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json

    import aoe2mc
    import scenarios
    from game import combat, run
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.four_civs(str(tmp_path / "s.aoe2scenario")), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data).setup()
        g.players = data["players"]
        conquest.crown(g, [g])
        assert len(g.kings) >= 2 and g.soldiers[g.kings[1]] == "KING"
        assert all("passed" in game.command(f"execute if entity {u}") for u in g.kings.values())
        rival = max(g.kings)
        conquest.tick(g)
        assert not g.ended
        game.command(f"kill {g.kings[rival]}")
        time.sleep(2)                                                  # a dead mob stays 20 ticks
        g.conquest_at = 0.0
        conquest.tick(g)
        assert rival in g.defeated
