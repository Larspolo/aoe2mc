"""game/per.py: an AI script counts the gaia objects that its team sees (#4965). The map of test_bot_gather."""
from test_bot_gather import bot_map

from game import gather, per

FAR = {"kind": "other", "name": "GOLD_MINE", "tile": [28.5, 2.5]}       # far from the bot (player 2) and its sight


def script():
    server, me, b = bot_map()
    b.g.data["objects"].append(dict(FAR))
    return per.Script(per.parse("(defrule (true) => (do-nothing))"), b), b, server


def test_count_the_seen_gold_mines_and_trees():
    s, b, _ = script()
    assert s.check(("up-gaia-type-count", "c:", "gold-mine", "==", 1))           # the near mine, not FAR
    assert s.check(("up-gaia-type-count", "c:", "tree", "==", 2))
    assert s.check(("up-gaia-type-count-total", "c:", "gold-mine", "==", 1))


def test_total_keeps_a_mine_that_the_team_saw_once():
    s, b, server = script()
    server.entities["b0"]["Pos"] = (27.5, 64.0, 3.5)                          # a villager walks to FAR
    assert s.check(("up-gaia-type-count", "c:", "gold-mine", "==", 2))
    server.entities["b0"]["Pos"] = (24.5, 64.0, 19.5)                         # and back home
    assert s.check(("up-gaia-type-count", "c:", "gold-mine", "==", 1))
    assert s.check(("up-gaia-type-count-total", "c:", "gold-mine", "==", 2))


def test_remaining_boar_amount():
    s, b, _ = script()
    assert s.check(("up-remaining-boar-amount", "==", 0))                     # no bot villager hunts (#4739)
    b.g.prey["boar"] = "WILD_BOAR"
    next(iter(b.g.villagers.values())).prey = "boar"
    assert s.check(("up-remaining-boar-amount", "==", gather.hunt_food("WILD_BOAR")))
    b.g.dead["boar"] = (5, 5)
    b.g.map.carcasses[(5, 5)] = 120
    assert s.check(("up-remaining-boar-amount", "==", 120))
