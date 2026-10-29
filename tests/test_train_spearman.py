"""game/train.py: an own barracks trains spearmen in the Feudal Age (#729): the cost and time of the data, and
the AoE2 values of combat.STATS (the bonus against cavalry)."""
import re

from test_forging import menus                                         # also the `aoe menu-add` parts (#1647)
from test_train_barracks import setup
from test_train_menu import entry

from game import combat, train


COST, TIME = train.COSTS["SPEARMAN"], train.TRAIN_TIMES["SPEARMAN"]


def feudal():
    server, g = setup(food=0, gold=0)
    g.stock.update(COST)
    g.techs.add("FEUDAL_AGE")
    return server, g


def slot(g, rect):
    return train.layout(g, rect)["SPEARMAN"][0]


def test_no_spearman_in_the_dark_age():
    server, g = setup(food=1000, gold=1000)
    g.stock.update(wood=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    before = dict(g.stock)
    assert f" {entry(g, rect, 'SPEARMAN')}{train.build.locked(g, 'SPEARMAN')}" in menus(server)[-1]
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0 and not g.queues.get(rect) and g.stock == before


def test_a_click_queues_one_spearman_in_the_feudal_age():
    server, g = feudal()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert f" {entry(g, rect, 'SPEARMAN')}queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", rect, slot(g, rect)) == 1 and g.queues[rect][0]["name"] == "SPEARMAN"
    assert all(g.stock[r] == 0 for r in COST)
    assert train.order(g, "Steve", rect, slot(g, rect)) == 0                       # no resources for a second one


def test_the_spearman_appears_after_its_train_time_with_its_aoe2_values():
    server, g = feudal()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, slot(g, rect))
    assert train.tick(g, TIME - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:zombie ", summon) and "trident" in summon
    assert g.soldiers == {uuid: "SPEARMAN"}
    assert combat.stats_command(uuid, "SPEARMAN") in server.log          # the bonus against cavalry
