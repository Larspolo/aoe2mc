"""game/combat.py, game/garrison.py: the Harbor and the Fortified Church take hits and shoot arrows (#1948)."""
from game import combat, garrison, train


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


def test_both_get_an_attack_with_range_reload_and_min_range(monkeypatch):
    for name in ("HARBOR", "FORTIFIED_CHURCH"):
        monkeypatch.setitem(combat.BUILDINGS, name, combat.BUILDINGS[name]._replace(bonus={"ship": 3, "spearman": 1}))   # test values (#5398)
        s, cmd = combat.BUILDINGS[name], line(name)
        assert cmd[12:16] == [str(s.attack), str(s.range * 4), str(round(s.reload / combat.NORMAL * 20)),
                              str(combat.FORT_MIN_RANGE[name] * 4)]
        assert cmd[-1] == ",".join(f"{c}:{n}" for c, n in sorted(s.bonus.items()))


def test_the_arrows_of_the_garrison():
    assert garrison.arrows("HARBOR", ["VILLAGER_MALE", "ARCHER"]) == garrison.arrows("HARBOR", []) + 2
    assert garrison.arrows("FORTIFIED_CHURCH", []) == 0
    assert garrison.arrows("FORTIFIED_CHURCH", ["VILLAGER_MALE"]) == 1
    assert garrison.arrows("FORTIFIED_CHURCH", ["VILLAGER_MALE", "VILLAGER_FEMALE", "ARCHER", "MONK"]) == 2


def test_a_harbor_of_the_map_is_a_target():
    data = {"objects": [{"kind": "building", "name": "HARBOR", "player": 1, "ref": 5, "footprint": [0, 0, 12, 12]},
                        {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "ref": 6, "uuid": "u6", "holder": 5}]}
    game = Game()
    combat.setup(game, data)
    assert any(c.startswith("summon slime ") for c in game.sent)
    h = combat.BUILDINGS["HARBOR"]
    assert f"aoe arrows {combat.target_uuid([0, 0, 12, 12])} {garrison.arrows('HARBOR', ['VILLAGER_MALE'])}" in game.sent
    assert any(c.startswith("aoe building ") and f" {h.hp} {h.melee} {h.pierce} " in c for c in game.sent)


def test_the_ungarrison_item_of_the_church_is_not_on_a_technology():
    slots = {train.ITEMS[n][0] for n in train.TRAINS.get("FORTIFIED_CHURCH", ())}
    assert garrison.ungarrison("FORTIFIED_CHURCH")[0] not in slots
