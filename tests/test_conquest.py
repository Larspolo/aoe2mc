"""game/conquest.py: the AoE2 conquest rule, a player without units and buildings is defeated (#1135)."""
import pytest
from test_cheat_end import game

from game import combat, conquest


def live(server, alive):
    """Let the fake server answer the selectors of conquest.alive: alive holds the players with a unit or building."""
    command = server.command

    def answer(cmd):
        if cmd.startswith("execute if entity @e[tag=aoe2mc."):
            server.log.append(cmd)
            n = int(cmd.split("aoe2mc.p")[-1].split(",")[0]) if "aoe2mc.p" in cmd else int(cmd.split("team=p")[1][0])
            return "Test passed, count: 1" if n in alive else "Test failed"
        return command(cmd)
    server.command = answer


def check(g):
    g.conquest_at = 0.0                                            # no wait of EVERY seconds
    conquest.tick(g)


def setup(players=(1, 2)):
    server, g = game()
    g.players = {str(p): {"color": "blue"} for p in (0,) + players}
    live(server, set(players))
    check(g)
    return server, g


def test_the_human_player_wins_when_player_2_has_nothing_left():
    server, g = setup()
    assert not g.ended
    live(server, {1})
    server.log.clear()
    check(g)
    assert "aoe destroy @e[tag=aoe2mc.building,team=p2]" in server.log            # cheats.destroy: the rest goes
    assert 'tellraw @a {"text": "Player 2 is defeated.", "color": "red"}' in server.log
    assert 'title @a[team=p1] title {"translate":"aoe2mc.victory","fallback":"Victory","color":"gold"}' in server.log and g.ended == "Victory"


def test_the_human_player_sees_defeat_with_nothing_left():
    server, g = setup()
    live(server, {2})
    server.log.clear()
    check(g)
    assert 'title @a[team=p1] title {"translate":"aoe2mc.defeat","fallback":"Defeat","color":"red"}' in server.log and g.ended == "Defeat"
    assert not any(c.startswith("aoe destroy") for c in server.log)


def test_the_game_goes_on_while_one_rival_is_left():
    server, g = setup((1, 2, 3))
    live(server, {1, 3})
    check(g)
    assert g.defeated == {2} and not g.ended
    live(server, {1})
    check(g)
    assert g.ended == "Victory"


def test_a_player_that_never_had_units_does_not_end_the_game():
    server, g = game()
    g.players = {"0": {}, "1": {}, "2": {}}
    live(server, {1})
    check(g)
    check(g)
    assert not g.ended and not g.defeated


def test_the_check_waits_between_two_runs():
    server, g = setup()
    live(server, set())
    conquest.tick(g)                                               # less than EVERY seconds after the last check
    assert not g.ended


def test_a_construction_site_keeps_a_player_alive():
    server, g = setup()
    g.sites.append({"name": "HOUSE", "player": 1, "progress": 0.2})
    live(server, {2})
    check(g)
    assert not g.ended


def test_the_selectors_skip_mounts_walls_and_gaia():
    server, g = setup()
    server.log.clear()
    conquest.alive(g, 2)
    assert server.log == ["execute if entity @e[tag=aoe2mc.p2,tag=!aoe2mc.mount]"]     # the first one passed
    server.log.clear()
    live(server, set())
    conquest.alive(g, 2)
    assert server.log[-1] == "execute if entity @e[tag=aoe2mc.building,team=p2,tag=!aoe2mc.wall]"   # no walls (#1322)


@pytest.mark.parametrize("name", ["PALISADE_WALL", "STONE_WALL", "FORTIFIED_WALL", "GATE", "PALISADE_GATE",
                                  "GATE_AA1", "CITY_WALL"])
def test_walls_and_gates_have_no_target_that_keeps_a_player_alive(name):
    assert name not in combat.BUILDINGS and not any(n.endswith(("_WALL", "_GATE")) for n in combat.BUILDINGS)
