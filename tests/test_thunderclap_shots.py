"""Thunderclap Bombs (#4369, AoE2 DE wiki): the shots of the Jurchen Rocket Carts, Lou Chuans and Grenadiers blast a
second time where they land, after a delay. The key "after_blast" of a technology of data/train.jsonl gives the
matching own units the plugin command `aoe afterblast` (train.fire_commands): test data here, not the values of the
data line (#4242). The plugin: a server."""
import shutil
import time

import pytest
from test_train_castle import setup

from game import combat, gather, run, train

BOMBS = [{"if": [{"names": ["GRENADIER"]}], "delay": 1.5, "attack": 4, "blast": 0.65, "times": 3},   # test data
         {"if": [{"names": ["LOU_CHUAN"]}], "delay": 2, "attack": 20, "blast": 2, "times": 1, "buildings": True}]


def ticks(seconds):
    return max(1, round(seconds / gather.NORMAL * 20))


def test_a_matching_unit_gets_the_delay_attack_blast_and_count_after_the_research(monkeypatch):
    monkeypatch.setitem(train.BY_KEY, "after_blast", {"THUNDERCLAP_BOMBS": BOMBS})
    monkeypatch.setattr(train, "FIRE", {})                                    # no blast at death here
    server, g = setup("JURCHENS", ages=3)
    assert train.fire_commands(g, "u", "GRENADIER") == []                     # no research: no second blast
    g.techs.add("THUNDERCLAP_BOMBS")
    T = g.map.T
    assert train.fire_commands(g, "u", "GRENADIER") == [f"aoe afterblast u {ticks(1.5)} 4 {0.65 * T:g} 3"]
    assert train.fire_commands(g, "u", "LOU_CHUAN") == [f"aoe afterblast u {ticks(2)} 20 {2 * T:g} 1 buildings"]
    assert train.fire_commands(g, "u", "MILITIA") == []                       # not in the tests
    assert train.fire_commands(g, "u", "GRENADIER", {"SIPHONS"}) == []        # only the techs of the call


def test_the_research_gives_the_live_units_the_blast_and_a_new_unit_too(monkeypatch):
    monkeypatch.setitem(train.BY_KEY, "after_blast", {"THUNDERCLAP_BOMBS": BOMBS})
    monkeypatch.setattr(train, "FIRE", {})                                    # no blast at death here
    server, g = setup("JURCHENS", ages=3)
    g.soldiers.update({"gr": "GRENADIER", "m": "MILITIA"})
    train.research(g, {"name": "THUNDERCLAP_BOMBS", "player": "Steve"})
    blasts = [c for c in server.log if c.startswith("aoe afterblast ")]
    assert blasts == train.fire_commands(g, "gr", "GRENADIER")


@pytest.mark.mc
def test_a_shot_blasts_again_after_the_delay_and_spares_the_own_unit(tiny_world, tmp_path):
    from test_fire_ship import uuid_of
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from test_siege_walk import summon
    from test_techs_thunderclap import health
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200                                                            # a floor in the air
    with run.Game(world) as game:
        game.command("forceload add -2 -2 30 30")
        game.command(f"fill 0 {y - 1} 0 23 {y - 1} 23 stone_bricks")
        game.command("time set midnight")
        game.command("team add red")
        game.command("team add blue")
        ids = {}
        # the Grenadier shoots at foe; own stands next to foe, inside the second blast
        for name, tag, x, z, team in (("GRENADIER", "g", 4.5, 10.5, "red"), ("MILITIA", "foe", 12.5, 10.5, "blue"),
                                      ("MILITIA", "own", 12.5, 12.0, "red")):
            assert "Summoned" in summon(game, name, x, y, z, tag), name
            ids[tag] = uuid_of(game, tag)
            assert "Stats: 1 units" in game.command(combat.stats_command(ids[tag], name))
            game.command(f"team join {team} @e[tag={tag}]")
            game.command(f"attribute {ids[tag]} minecraft:movement_speed base set 0")
        for tag in ("foe", "own"):
            game.command(f"data merge entity {ids[tag]} {{NoAI:1b}}")
        game.command(combat.range_command(ids["g"], "GRENADIER", 4))
        attack, delay = 5, 60                                          # 3 s: the arrow hit comes first
        assert game.command(f"aoe afterblast {ids['g']} {delay} {attack} 3 2").strip() == "Afterblast: 1 units"
        full, own = health(game, ids["foe"]), health(game, ids["own"])
        assert game.command(f"aoe attack {ids['g']} {ids['foe']}").strip() == "Attack: 1 units"
        end = time.time() + 10
        while health(game, ids["foe"]) == full and time.time() < end:
            time.sleep(0.05)
        game.command(f"aoe stop {ids['g']}")                           # one shot only
        shot = health(game, ids["foe"])
        assert shot < full                                             # the arrow hit
        time.sleep(1)
        assert health(game, ids["foe"]) == shot                        # no second blast before the delay
        time.sleep(3)
        blast = 2 * max(1, attack - combat.stats("MILITIA").melee)      # two melee hits of attack
        assert health(game, ids["foe"]) == pytest.approx(shot - blast, abs=0.5)
        assert health(game, ids["own"]) == own                         # no harm to the own unit
