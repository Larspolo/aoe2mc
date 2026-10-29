"""The diplomacy stance neutral (#1645): the units of a player do not attack the units of a neutral player by
themselves, but an order does. aoe2mc.json `players[N]["neutral"]`, gather.neutral_command and `aoe neutral`."""
import json
import shutil
import time

import pytest
from AoE2ScenarioParser.datasets.players import PlayerId
from AoE2ScenarioParser.datasets.trigger_lists import DiplomacyState

import aoe2mc
import scenarios
from game import combat, gather, run
from test_damage import health
from test_gather import FakeServer, grid

UNITS = [{"kind": "unit", "name": "MILITIA", "player": p, "uuid": f"m-{p}", "tile": [2.5 + p, 2.5]} for p in (1, 2, 3)]


def neutral_scenario(path):
    """A small scenario where player 1 is neutral to player 2 (one way) and player 2 is an enemy of player 1."""
    scn = scenarios.new_scenario(24)
    scn.player_manager.players[1].set_player_diplomacy(PlayerId.TWO, DiplomacyState.NEUTRAL)
    return scenarios.save(scn, path)


def players(tmp_path, neutral):
    path = str(tmp_path / "n.aoe2scenario")
    (neutral_scenario if neutral else scenarios.tiny)(path)
    return aoe2mc.read_scenario(path)[-1]


def test_a_neutral_stance_of_the_scenario_is_in_the_players(tmp_path):
    p = players(tmp_path, True)
    assert p[1]["neutral"] == [2] and "neutral" not in p[2]              # one way, as in the scenario


def test_a_scenario_with_no_stances_has_no_neutral_key(tmp_path):
    assert not any("neutral" in p for p in players(tmp_path, False).values())


def test_aoe2mc_json_keeps_the_neutral_stances(tmp_path):
    src = neutral_scenario(str(tmp_path / "n.aoe2scenario"))
    aoe2mc.main([src, str(tmp_path / "W")])
    with open(tmp_path / "W" / "aoe2mc.json") as f:
        p = json.load(f)["players"]
    assert p["1"]["neutral"] == [2] and "neutral" not in p["2"]


def test_neutral_command():
    assert gather.neutral_command({"1": {"neutral": [2, 3]}, "2": {"neutral": [1]}, "3": {}}) == \
        "aoe neutral p1:p2,p3 p2:p1"
    assert gather.neutral_command({"1": {"team": 1}}) == "aoe neutral -" == gather.neutral_command({})


def test_the_game_sends_the_stances_and_a_neutral_unit_takes_an_attack_order():
    data = grid([[64] * 10 for _ in range(10)], UNITS)
    data["players"] = {"1": {"civ": "BRITONS", "neutral": [2]}, "2": {"civ": "FRANKS"}, "3": {"civ": "MAYANS"}}
    server = FakeServer({})
    server.kind = "paper"
    g = gather.Gather(server, data).setup()
    assert "aoe neutral p1:p2" in server.log                            # the plugin skips p2 in the automatic targets
    assert set(g.enemies) == {"m-2", "m-3"}                             # a click on m-2 still orders the attack
    g.selected = {"m-1"}
    g.soldiers["m-1"] = "MILITIA"
    g.attack("m-2")
    assert any(c.startswith("aoe attack") and c.endswith(" m-2") for c in server.log)


@pytest.mark.mc
def test_a_soldier_leaves_a_neutral_unit_alone_and_attacks_it_on_an_order(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    x0, y, z0 = 1, 200, 1                     # a floor in the air, inside the world border
    with run.Game(world) as game:
        game.command(f"forceload add {x0 - 2} {z0 - 2} {x0 + 30} {z0 + 30}")
        game.command(f"fill {x0 - 1} {y - 1} {z0 - 1} {x0 + 26} {y - 1} {z0 + 26} stone_bricks")
        game.command("time set midnight")
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        assert game.command("aoe neutral p1:p2").startswith("Neutral:")
        # the champion a sees the militia b 3 tiles away (T = 4): with the stance neutral it does not attack
        for tag, (dx, team, name) in {"a": (2, "p1", "CHAMPION"), "b": (14, "p2", "MILITIA")}.items():
            game.command(f'summon zombie {x0 + dx + 0.5} {y} {z0 + 2.5} {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join {team} @e[tag={tag}]")
            assert game.command(combat.stats_command(f"@e[tag={tag},limit=1]", name)).strip() == "Stats: 1 units"
        assert game.command(combat.sight_command("@e[tag=a,limit=1]", "CHAMPION", 4)).strip() == "Sight: 1 units"
        time.sleep(5)
        assert health(game, "b") == float(combat.stats("MILITIA").hp)     # no automatic attack on a neutral
        game.command("aoe attack @e[tag=a,limit=1] @e[tag=b,limit=1]")
        end = time.time() + 60
        while time.time() < end and health(game, "b") is not None:
            time.sleep(0.2)
        assert health(game, "b") is None                                  # the order makes the attack
