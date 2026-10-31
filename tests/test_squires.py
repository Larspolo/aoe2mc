"""game/train.py: the barracks researches Squires (AoE2 DE wiki infobox): the live and the new infantry of the player
walk faster, other units do not change (#1415)."""
import re

import lang
import pytest
from test_forging import menus, setup

from game import ai, gather, train

BARRACKS = (17, 3)


def castle(food=100):
    server, g = setup(food=food)
    g.techs.add("CASTLE_AGE")
    return server, g


def test_the_barracks_menu_has_squires_from_its_age():
    slot, item, label = train.slots("BARRACKS", "SQUIRES")
    for server, g in (setup(), castle()):
        train.open_menu(g, "Steve", BARRACKS)
        assert (f" {slot}:{item}:{label}:" in menus(server)[-1]) == train.unlocked(g, "SQUIRES")
    assert train.unlocked(g, "SQUIRES")                                # the Castle Age has it


def test_squires_makes_the_live_and_the_new_infantry_walk_faster():
    sq, militia = train.COSTS["SQUIRES"], train.COSTS["MILITIA"]
    server, g = castle(food=sq.get("food", 0) + militia.get("food", 0))
    g.stock["gold"] = militia.get("gold", 0)
    rect = train.open_menu(g, "Steve", BARRACKS)
    assert train.speed(g, "MILITIA") == 1
    assert train.order(g, "Steve", rect, train.slots("BARRACKS", "SQUIRES")[0]) == 1
    assert g.stock["food"] == militia.get("food", 0)
    server.log.clear()
    train.tick(g, train.TRAIN_TIMES["SQUIRES"])
    label = train.slots("BARRACKS", "SQUIRES")[2]
    assert "SQUIRES" in g.techs and f"{label} is researched." in " ".join(map(lang.english, server.log))
    f = train.speed(g, "MILITIA")
    assert f > 1 and train.speed(g, "SPEARMAN") == pytest.approx(f)
    assert train.speed(g, "SCOUT_CAVALRY") == train.speed(g, "ARCHER") == train.speed(g, "VILLAGER_MALE") == 1
    assert ai.speed_command("m", "MILITIA", g.map.T, gather.NORMAL * f) in server.log           # the live militia
    assert not any(c.startswith(("aoe speed s ", "aoe speed a ")) for c in server.log)              # not the others
    assert train.order(g, "Steve", rect, train.slots("BARRACKS", "MILITIA")[0]) == 1               # a new militia
    new, = train.tick(g, train.TRAIN_TIMES["MILITIA"])
    assert any(re.fullmatch(re.escape(ai.speed_command(new, "MILITIA", g.map.T, gather.NORMAL * f)), c) for c in server.log)
