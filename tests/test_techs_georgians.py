"""Svan Towers of the Georgians, with test data (#4282): the towers get more attack and arrows that pass through the
units ("pass_arrows" of data/train.jsonl). The values of the data line do not matter here (owner, #4242)."""
import shutil
import time

import pytest
import train as plain_train  # garrison imports train by its plain name (not game.train)
from test_train_castle import setup

from game import combat, garrison, run, train

PASS = {"names": ["TOWN_CENTER"], "tiles": 2, "part": 0.25}


def test_a_researched_technology_lets_the_arrows_of_its_buildings_pass_through(monkeypatch):
    tech = next(t for t in train.TECHS if t not in train.BY_KEY["pass_arrows"])          # train.stats needs a real name
    for m in (train, plain_train):
        monkeypatch.setitem(m.BY_KEY["pass_arrows"], tech, PASS)
    server, g = setup("GEORGIANS")
    rect = next(r for r, o in garrison.holders(g).items() if o["name"] == "TOWN_CENTER")
    before = garrison.arrows_command(g, rect)
    assert len(before.split()) == 4 and train.pass_arrows(g, "TOWN_CENTER") == ""
    sent, command = [], g.command
    g.command = lambda c: (sent.append(c), command(c))[1]
    train.research(g, {"name": tech, "player": "Steve"})              # a queue entry
    after = garrison.arrows_command(g, rect)
    assert after == f"{before} {2 * g.map.T} 0.25" and after in sent
    assert train.pass_arrows(g, "WATCH_TOWER") == ""                   # not in the names


def test_the_building_command_ends_its_arrows_with_the_pass():
    box = (0, 60, 0, 7, 70, 7)
    uuid = combat.target_uuid([0, 0, 8, 8])
    plain = [c for c in combat.building(uuid, "WATCH_TOWER", 1, box) if c.startswith("aoe arrows")]
    through = [c for c in combat.building(uuid, "WATCH_TOWER", 1, box, through=" 8 0.5") if c.startswith("aoe arrows")]
    assert through == [plain[0] + " 8 0.5"]


def test_an_effect_on_tower_names_adds_attack():
    s = combat.stats("WATCH_TOWER")
    t = train.effect({"if": [{"names": ["WATCH_TOWER"]}], "add": {"attack": 2}})("WATCH_TOWER", s)
    assert t.attack == s.attack + 2
    assert train.effect({"if": [{"names": ["WATCH_TOWER"]}], "add": {"attack": 2}})("KNIGHT", combat.stats("KNIGHT")) \
        == combat.stats("KNIGHT")


@pytest.mark.mc
def test_the_arrow_of_a_tower_with_svan_towers_hurts_the_unit_behind_on_a_server(tiny_world, tmp_path):
    """The plugin reads the pass of `aoe arrows`: the arrow at the near enemy also hurts the enemy behind it on its line
    (#4282)."""
    from test_damage import health
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    y = 200
    box = (20, y, 20, 23, y + 40, 23)                                  # a guard tower of 1 x 1 tiles (T = 4)
    uuid = combat.target_uuid([20, 20, 24, 24])
    with run.Game(world) as game:
        game.command("forceload add 0 0 80 80")
        game.command(f"fill 0 {y - 1} 0 79 {y - 1} 79 stone_bricks")
        game.command("time set midnight")                              # zombies burn in the sun
        for t in ("p1", "p2"):
            game.command(f"team add {t}")
        for tag, x in (("a", 34.5), ("b", 40.5)):                      # 12 and 18 blocks from the middle of the tower
            game.command(f'summon zombie {x} {y} 22.0 {{NoAI:1b,IsBaby:0b,Tags:["{tag}"]}}')
            game.command(f"team join p2 @e[tag={tag}]")
            assert game.command(f"aoe stats @e[tag={tag},limit=1] 1000 4 0 1 0 archer - 20").strip() == "Stats: 1 units"
        for c in combat.building(uuid, "GUARD_TOWER", 1, box, through=" 8 0.5"):
            assert "Bad" not in game.command(c)
        end = time.time() + 20
        while 1000.0 in (health(game, "a"), health(game, "b")) and time.time() < end:
            time.sleep(0.2)
        assert health(game, "a") < 1000 and health(game, "b") < 1000, (health(game, "a"), health(game, "b"))
