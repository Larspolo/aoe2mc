"""game/train.py: the monastery researches Fervor (140 gold, 50 s: monks walk 15 % faster) and Sanctity (175 gold,
60 s: monks get 15 more hit points) in the Castle Age, as on the AoE2 wiki infoboxes (#1261)."""
import re

import pytest
from test_monk_train import MONASTERY, monastery

from game import ai, combat, gather, train


def research(g, slot, gold):
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, slot) == 1 and g.stock["gold"] == 0
    return rect


def test_the_costs_times_and_age_are_those_of_aoe2():
    assert train.COSTS["FERVOR"] == {"gold": 140} and train.TRAIN_TIMES["FERVOR"] == 50
    assert train.COSTS["SANCTITY"] == {"gold": 175} and train.TRAIN_TIMES["SANCTITY"] == 60
    assert train.TECH_AGE["FERVOR"] == train.TECH_AGE["SANCTITY"] == 2
    assert train.HELP["FERVOR"] and train.HELP["SANCTITY"]


def test_before_the_castle_age_the_menu_has_no_monastery_technology():
    server, g = monastery(age=1)
    train.open_menu(g, "Steve", MONASTERY)
    assert "Fervor" not in server.log[-1] and "Sanctity" not in server.log[-1]


def test_sanctity_gives_the_live_and_the_new_monks_15_hit_points():
    server, g = monastery(gold=275)
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, 0) == 1                       # a monk: 100 gold, 51 s
    old, = train.tick(g, 51)
    research(g, 2, 175)
    server.log.clear()
    train.tick(g, 60)
    assert combat.stats_command(old, "MONK", train.stats(g, "MONK")) in server.log
    assert train.stats(g, "MONK").hp == combat.stats("MONK").hp + 15
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")       # only monks
    assert "Sanctity is researched" in " ".join(server.log)


def test_fervor_makes_the_live_monks_walk_15_percent_faster():
    server, g = monastery(gold=240)
    rect = train.open_menu(g, "Steve", MONASTERY)
    train.order(g, "Steve", rect, 0)
    old, = train.tick(g, 51)
    assert train.speed(g, "MONK") == 1
    research(g, 1, 140)
    server.log.clear()
    train.tick(g, 50)
    assert train.speed(g, "MONK") == pytest.approx(1.15) and train.speed(g, "MILITIA") == 1
    cmd = ai.speed_command(old, "MONK", g.map.T, gather.NORMAL * 1.15)
    assert cmd in server.log and cmd != ai.speed_command(old, "MONK", g.map.T, gather.NORMAL)
    g.stock["gold"] = 100                                              # a new monk gets the speed at once
    train.order(g, "Steve", rect, 0)
    new, = train.tick(g, 51)
    assert any(re.fullmatch(re.escape(ai.speed_command(new, "MONK", g.map.T, gather.NORMAL * 1.15)), c) for c in server.log)
