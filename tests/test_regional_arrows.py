"""game/combat.py, game/garrison.py: the Harbor and the Fortified Church take hits and shoot arrows (#1948)."""
from game import combat, garrison


class Game:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return "Stats: 1 units"


def line(name):
    """The `aoe building` command of building `name` (a 3 x 3 tile footprint at T = 4)."""
    cmds = combat.building("00000000-0000-0000-0000-000000000001", name, 1, (0, 64, 0, 11, 104, 11))
    return next(c for c in cmds if c.startswith("aoe building ")).split()


def test_the_values_of_the_wiki():
    h, c = combat.BUILDINGS["HARBOR"], combat.BUILDINGS["FORTIFIED_CHURCH"]
    assert (h.hp, h.attack, h.melee, h.pierce, h.range, h.reload) == (2000, 3, 3, 10, 7, 3.0)
    assert h.bonus == {"camel": 1, "ship": 3} and c.bonus == {"camel": 1, "ship": 5}
    assert (c.hp, c.attack, c.melee, c.pierce, c.range) == (2400, 5, 4, 10, 4)
    assert combat.FORT_MIN_RANGE["HARBOR"] == combat.FORT_MIN_RANGE["FORTIFIED_CHURCH"] == 1
    assert garrison.SIZES["HARBOR"] == garrison.SIZES["FORTIFIED_CHURCH"] == 10
    assert combat.STONE in h.classes and combat.STONE in c.classes             # wiki class "Stone Defense"


def test_both_get_an_attack_with_range_reload_and_min_range():
    h, c = line("HARBOR"), line("FORTIFIED_CHURCH")
    assert h[12:16] == ["3", str(7 * 4), str(round(3.0 / combat.NORMAL * 20)), "4"]
    assert c[12:16] == ["5", str(4 * 4), str(round(2.0 / combat.NORMAL * 20)), "4"]
    assert h[-1] == "camel:1,ship:3" and c[-1] == "camel:1,ship:5"


def test_the_arrows_of_the_garrison():
    assert garrison.arrows("HARBOR", []) == 4
    assert garrison.arrows("HARBOR", ["VILLAGER_MALE", "ARCHER"]) == 6
    assert garrison.arrows("FORTIFIED_CHURCH", []) == 0
    assert garrison.arrows("FORTIFIED_CHURCH", ["VILLAGER_MALE"]) == 1
    assert garrison.arrows("FORTIFIED_CHURCH", ["VILLAGER_MALE", "VILLAGER_FEMALE", "ARCHER", "MONK"]) == 2


def test_a_harbor_of_the_map_is_a_target():
    data = {"objects": [{"kind": "building", "name": "HARBOR", "player": 1, "ref": 5, "footprint": [0, 0, 12, 12]},
                        {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "ref": 6, "uuid": "u6", "holder": 5}]}
    game = Game()
    combat.setup(game, data)
    assert any(c.startswith("summon slime ") for c in game.sent)
    assert f"aoe arrows {combat.target_uuid([0, 0, 12, 12])} 5" in game.sent
    assert any(c.startswith("aoe building ") and " 2000 3 10 " in c for c in game.sent)


def test_the_ungarrison_item_of_the_church_is_not_on_a_technology():
    assert garrison.ungarrison("FORTIFIED_CHURCH")[0] == 26
