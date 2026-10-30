"""Battle Drills one age earlier for the Thracians (#2481, epic #1088). The game program has no Levy: the Chronicles
civilizations train the militia line, and Battle Drills is the Chronicles form of the Two-Handed Swordsman upgrade
(AoE2 wiki "Battle Drills"). So the Thracians get that upgrade in the Castle (Classical) Age."""
from menu_line import item
from test_civ_earlier import setup
from test_train_castle import menus

from game import train

UPGRADE = "TWO_HANDED_SWORDSMAN_UPGRADE"


def g(civ, ages):
    _, g = setup(civ, ages)
    g.techs.add(train.BY_KEY["after"][UPGRADE])                                  # Long Swordsman before it
    return g


def test_a_thracian_player_researches_it_in_the_castle_age():
    assert train.unlocked(g("THRACIANS", 2), UPGRADE)
    assert not train.unlocked(g("THRACIANS", 1), UPGRADE)


def test_the_other_civilizations_need_the_imperial_age():
    for civ in ("SPARTANS", "BRITONS"):
        assert not train.unlocked(g(civ, 2), UPGRADE)
        assert train.unlocked(g(civ, 3), UPGRADE)


def test_the_barracks_menu_of_the_castle_age():
    def line(civ):
        server, x = setup(civ, 2)
        x.techs.update(["MAN_AT_ARMS_UPGRADE", "LONG_SWORDSMAN_UPGRADE"])   # the upgrades before it
        x.data["objects"].append({"kind": "building", "name": "BARRACKS", "player": 1, "tile": [18.0, 12.0],
                                  "footprint": [16, 10, 20, 14]})
        train.open_menu(x, "Steve", (18, 12))
        return item(menus(server)[-1], "Two-Handed Swordsman")
    assert line("THRACIANS") is not None and "Needs" not in line("THRACIANS")
    assert line("SPARTANS") is None                                    # the next upgrade shows from its age on
