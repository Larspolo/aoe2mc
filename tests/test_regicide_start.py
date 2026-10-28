"""#2388: a Regicide game (run.py --play --mode regicide) starts as in AoE2 DE (wiki "Regicide (game mode)"): the
Regicide starting resources of each level, a Castle and more villagers next to the town center, and the technology
Treason at the Castle in place of Spies: it shows the enemy Kings."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import gather  # noqa: E402
import regicide  # noqa: E402
import train  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402
from test_regicide import game  # noqa: E402

REGICIDE = regicide.MODES["regicide"]


@pytest.mark.parametrize("level, start", [("standard", (500, 500, 0, 150)), ("low", (500, 500, 0, 150)),
                                          ("medium", (750, 750, 0, 225)), ("high", (1000, 1000, 0, 300))])
def test_the_regicide_starting_resources(level, start):
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 2, 6, 6]}]
    g = gather.Gather(FakeServer({}), grid([[64] * 20 for _ in range(20)], objects), resources=level).setup()
    regicide.start(g, REGICIDE, level)
    assert tuple(g.stock[r] for r in ("food", "wood", "gold", "stone")) == start
    assert f"scoreboard players set Stone aoe_res {start[3]}" in g.game.log


def test_ultra_keeps_its_resources():
    g = gather.Gather(FakeServer({}), grid([[64] * 20 for _ in range(20)]), resources="ultra").setup()
    regicide.start(g, REGICIDE, "ultra")
    assert g.stock["gold"] == gather.LEVELS["ultra"]["gold"]


def test_a_player_gets_a_castle_site_and_more_villagers(monkeypatch):
    server, g, spy = game()
    monkeypatch.setattr(train, "summon", spy)
    stock = dict(g.stock)
    regicide.setup(g)
    names = [name for name, player, pos in server.summoned if player == 1]
    assert names.count("KING") == 1 and names.count("VILLAGER_MALE") == REGICIDE["more"]["VILLAGER_MALE"] == 7
    castle, = [s for s in g.sites if s["name"] == "CASTLE"]
    assert castle["player"] == 1 and castle["progress"] == 0.0 and g.stock == stock   # a free site
    assert not [n for n, p, _ in server.summoned if p == 2]       # player 2 has its King: no new start items


def imperial(mode):
    server, g, _ = game()
    g.techs.update({"FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE"})
    g.mode = mode
    return server, g


def test_treason_is_at_the_castle_only_in_regicide():
    _, g = imperial("regicide")
    assert train.unlocked(g, "TREASON") and not train.unlocked(g, "SPIES")
    _, g = imperial("standard")
    assert train.unlocked(g, "SPIES") and not train.unlocked(g, "TREASON")
    assert "TREASON" in train.TRAINS["CASTLE"]


def test_treason_shows_the_enemy_kings_each_time():
    server, g = imperial("regicide")
    for _ in range(2):
        assert train.repeatable(g, "TREASON")
        train.research(g, {"name": "TREASON", "player": "Steve"})
    glow = [c for c in server.log if "minecraft:glowing" in c]
    assert glow.count("effect give @e[tag=aoe2mc.p2,tag=aoe2mc.king] minecraft:glowing 10 0 true") == 2
    assert not [c for c in glow if "aoe2mc.p1," in c]             # not the own King
