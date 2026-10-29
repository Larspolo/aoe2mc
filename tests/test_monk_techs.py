"""game/train.py: the monastery researches Fervor (monks walk faster) and Sanctity (monks get more hit points) in the
Castle Age, as on the AoE2 wiki infoboxes (#1261). The costs, times and values come from the data."""
import re

from test_monk_train import MONASTERY, monastery

from game import ai, combat, gather, train


def research(g, slot, gold):
    g.stock["gold"] = gold
    rect = train.open_menu(g, "Steve", MONASTERY)
    assert train.order(g, "Steve", rect, slot) == 1 and g.stock["gold"] == 0
    return rect


def learn(g, name):
    """research() of the technology name with just its gold (the data)."""
    return research(g, train.SLOTS[name], train.price(g, name)["gold"])


def monk(g, rect):
    """A new monk of the monastery rect."""
    g.stock["gold"] += train.price(g, "MONK")["gold"]
    assert train.order(g, "Steve", rect, train.SLOTS["MONK"]) == 1
    uuid, = train.tick(g, train.seconds(g, "MONK", "MONASTERY"))
    return uuid


def test_before_the_castle_age_the_menu_has_no_monastery_technology():
    server, g = monastery(age=1)
    train.open_menu(g, "Steve", MONASTERY)
    assert "Fervor" not in server.log[-1] and "Sanctity" not in server.log[-1]


def test_sanctity_gives_the_live_and_the_new_monks_more_hit_points():
    server, g = monastery(gold=0)
    old = monk(g, train.open_menu(g, "Steve", MONASTERY))
    learn(g, "SANCTITY")
    server.log.clear()
    train.tick(g, train.seconds(g, "SANCTITY", "MONASTERY"))
    assert combat.stats_command(old, "MONK", train.stats(g, "MONK")) in server.log
    assert train.stats(g, "MONK").hp > combat.stats("MONK").hp
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")       # only monks
    assert "Sanctity is researched" in " ".join(server.log)


def test_fervor_makes_the_live_monks_walk_faster():
    server, g = monastery(gold=0)
    rect = train.open_menu(g, "Steve", MONASTERY)
    old = monk(g, rect)
    assert train.speed(g, "MONK") == 1
    learn(g, "FERVOR")
    server.log.clear()
    train.tick(g, train.seconds(g, "FERVOR", "MONASTERY"))
    fast = train.speed(g, "MONK")
    assert fast > 1 and train.speed(g, "MILITIA") == 1
    cmd = ai.speed_command(old, "MONK", g.map.T, gather.NORMAL * fast)
    assert cmd in server.log and cmd != ai.speed_command(old, "MONK", g.map.T, gather.NORMAL)
    new = monk(g, rect)                                                # a new monk gets the speed at once
    assert any(re.fullmatch(re.escape(ai.speed_command(new, "MONK", g.map.T, gather.NORMAL * fast)), c) for c in server.log)
