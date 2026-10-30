"""game/cheats.py: the AoE2 cheats that end a game or destroy players (#819)."""
import time

import pytest
from test_gather import FakeServer, grid

from game import cheats, combat, gather


def game(on=True):
    """Player 1 with a villager and a militia, player 2 with a house and a militia, player 3 with a scout, a deer."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v-1", "tile": [2.5, 2.5]},
               {"kind": "unit", "name": "MILITIA", "player": 1, "uuid": "m-1", "tile": [3.5, 2.5]},
               {"kind": "unit", "name": "MILITIA", "player": 2, "uuid": "m-2", "tile": [12.5, 12.5]},
               {"kind": "unit", "name": "SCOUT_CAVALRY", "player": 3, "uuid": "s-3", "tile": [15.5, 3.5]},
               {"kind": "unit", "name": "DEER", "player": 0, "uuid": "d-0", "tile": [8.5, 8.5]},
               {"kind": "building", "name": "HOUSE", "player": 2, "footprint": [10, 10, 12, 12]}]
    feet = {"v-1": (2.5, 64.0, 2.5), "m-1": (3.5, 64.0, 2.5), "m-2": (12.5, 64.0, 12.5), "d-0": (8.5, 64.0, 8.5)}
    server = FakeServer({u: {"Pos": p} for u, p in feet.items()} | {"Steve": {}})
    return server, gather.Gather(server, grid([[64] * 20 for _ in range(20)], objects), cheats=on).setup()


def cheat(server, g, code):
    server.scores["aoe_cheat"] = cheats.NAMES.index(code) + 1
    server.log.clear()
    g.clicks()
    return server.log


def test_torpedo_destroys_one_player():
    server, g = game()
    house = combat.target_uuid([10, 10, 12, 12])
    assert set(g.enemies) == {"m-2", "s-3"} and house in g.forts
    log = cheat(server, g, "torpedo2")
    assert "aoe destroy @e[tag=aoe2mc.building,team=p2]" in log
    assert "kill @e[team=p2,type=!player]" in log and "kill @e[tag=aoe2mc.p2]" in log
    assert log.index("execute as @e[tag=aoe2mc.p2] on vehicle run kill @s") < log.index("kill @e[tag=aoe2mc.p2]")
    assert not any("p1" in c or "p3" in c for c in log if c.startswith(("kill", "aoe destroy")))
    assert set(g.enemies) == {"s-3"} and house in g.sieged          # Gather.fall frees its footprint
    assert set(g.villagers) == {"v-1"} and not g.ended


def test_black_death_destroys_all_other_players():
    server, g = game()
    log = cheat(server, g, "black death")
    assert [c for c in log if c.startswith("aoe destroy")] == [f"aoe destroy @e[tag=aoe2mc.building,team=p{n}]"
                                                                for n in (2, 3)]
    assert not g.enemies and not any("p1" in c for c in log if c.startswith("kill"))


def test_wimpywimpywimpy_destroys_the_own_player_and_ends_the_game():
    server, g = game()
    g.select("m-1")
    log = cheat(server, g, "wimpywimpywimpy")
    assert "kill @e[team=p1,type=!player]" in log and not g.villagers and not g.soldiers and not g.selected
    assert 'title @a[team=p1] title {"text":"Defeat","color":"red"}' in log and g.ended == "Defeat"


def test_i_r_winner_shows_victory_and_stops_the_play_loop():
    server, g = game()
    log = cheat(server, g, "i r winner")
    assert 'title @a[team=p1] title {"text":"Victory","color":"gold"}' in log and g.ended == "Victory"
    t = time.time()
    g.run(seconds=5)
    assert time.time() - t < 1


def test_resign_shows_defeat():
    server, g = game()
    assert 'title @a[team=p1] title {"text":"Defeat","color":"red"}' in cheat(server, g, "resign") and g.ended == "Defeat"


def test_natural_wonders_gives_the_animals_and_takes_the_own_units():
    server, g = game()
    g.select("v-1")
    log = cheat(server, g, "natural wonders")
    assert g.soldiers == {"d-0": "DEER"} and not g.villagers and not g.selected
    assert 'tellraw Steve {"text":"You control nature: 1 animals"}' in log
    g.select("d-0")
    assert g.selected == {"d-0"}


def test_the_codes_do_nothing_with_cheats_off():
    server, g = game(on=False)
    for code in ("torpedo2", "i r winner", "natural wonders"):
        log = cheat(server, g, code)
        assert not any(c.startswith(("kill", "aoe destroy", "title @a[team=p1] title")) for c in log)
    assert not g.ended and set(g.enemies) == {"m-2", "s-3"} and set(g.villagers) == {"v-1"}


@pytest.mark.mc
def test_torpedo_removes_player_2_on_a_server(tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    import contextlib
    import io
    import json

    import scenarios

    import aoe2mc
    from game import run
    with contextlib.redirect_stdout(io.StringIO()):
        aoe2mc.convert(scenarios.four_civs(str(tmp_path / "s.aoe2scenario")), str(tmp_path / "W"))
    data = json.load(open(tmp_path / "W" / "aoe2mc.json"))
    ground = [r.split() for r in data["ground"]]
    houses = [o for o in data["objects"] if o["kind"] == "building" and o["player"] == 2 and o["name"] == "HOUSE"]
    with run.Game(tmp_path / "W") as game:
        game.forceload()
        combat.setup(game, data)
        g = gather.Gather(game, data, cheats=True).setup()

        def alive(p):
            return sum("passed" in game.command(f"execute if entity {o['uuid']}") for o in data["objects"]
                       if o["kind"] == "unit" and o["player"] == p and o.get("uuid"))

        def solid(o):                                                  # blocks of the corner column of a house
            x0, y0, z0, *_ = combat.building_box(o, ground)
            return sum("passed" not in game.command(f"execute if block {x0} {y} {z0} minecraft:air")
                       for y in range(y0 + 1, y0 + 4))
        ones, twos = alive(1), alive(2)
        assert ones and twos and houses and all(solid(o) for o in houses)
        game.command("team join p2 @e[tag=aoe2mc.p2,team=]")          # the pulse of the datapack, at once
        sent, command = [], game.command
        game.command = lambda c: sent.append((c, command(c))) or sent[-1][1]
        cheats.apply(g, "aoe2mc", "torpedo2")
        game.command = command
        time.sleep(2)                                                  # a dead mob stays 20 ticks
        assert alive(2) == 0 and alive(1) == ones, sent
        assert not any("passed" in game.command(f"execute if entity {combat.target_uuid(o['footprint'])}")
                       for o in houses)                                # the targets of the buildings are gone
        assert not any(solid(o) for o in houses)                       # the plugin filled their boxes with air
