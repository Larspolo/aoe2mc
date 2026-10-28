"""game/train.py: an own barracks trains spearmen in the Feudal Age (#729): 35 food and 25 wood, 22 AoE2 seconds,
and the AoE2 values of combat.STATS (the bonus against cavalry)."""
import re

from test_forging import menus                                         # also the `aoe menu-add` parts (#1647)
from test_train_barracks import setup

from game import combat, train


def feudal(food=35, wood=25):
    server, g = setup(food=food)
    g.stock.update(wood=wood)
    g.techs.add("FEUDAL_AGE")
    return server, g


def test_no_spearman_in_the_dark_age():
    server, g = setup(food=1000)
    g.stock.update(wood=1000)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert "1:gray_dye:Spearman:35 food · 25 wood · 22 s · Needs the Feudal Age" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 1) == 0 and not g.queues.get(rect) and g.stock["wood"] == 1000


def test_a_click_queues_one_spearman_in_the_feudal_age():
    server, g = feudal()
    rect = train.open_menu(g, "Steve", (11, 3))
    assert "1:zombie_spawn_egg:Spearman:35 food · 25 wood · 22 s · queue 0/15" in menus(server)[-1]
    assert train.order(g, "Steve", rect, 1) == 1 and g.queues[rect][0]["name"] == "SPEARMAN"
    assert g.stock["food"] == 0 and g.stock["wood"] == 0
    assert train.order(g, "Steve", rect, 1) == 0                       # no resources for a second one


def test_the_spearman_appears_after_22_seconds_with_its_aoe2_values():
    server, g = feudal()
    rect = train.open_menu(g, "Steve", (11, 3))
    train.order(g, "Steve", rect, 1)
    assert train.tick(g, 21) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    assert re.match(r"summon minecraft:zombie ", summon) and "trident" in summon
    assert g.soldiers == {uuid: "SPEARMAN"}
    assert combat.stats_command(uuid, "SPEARMAN") in server.log          # the bonus against cavalry
