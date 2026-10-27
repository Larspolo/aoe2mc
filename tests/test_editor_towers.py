"""The Sea Tower, the Fire Tower and the Fortress of the Scenario Editor take hits and shoot (AoE2 wiki, #2137)."""
from game import combat, garrison, train

UUID = "00000000-0000-0000-0000-000000000001"
BOX = (8, 64, 8, 23, 104, 23)


def shot(name):
    """attack, range in blocks, reload in ticks, minimum range in blocks of the `aoe building` line of name."""
    line = next(c for c in combat.building(UUID, name, 1, BOX) if c.startswith("aoe building "))
    return tuple(map(int, line.split()[12:16]))


def test_editor_towers_shoot_with_their_wiki_values():
    assert shot("SEA_TOWER") == (7, 32, round(2.0 / combat.NORMAL * 20), 4)
    assert shot("FIRE_TOWER") == (7, 20, round(0.25 / combat.NORMAL * 20), 4)
    assert shot("FORTRESS") == (12, 40, round(2.5 / combat.NORMAL * 20), 4)
    assert combat.stats("FORTRESS").hp == 4800 and combat.stats("SEA_TOWER").bonus["ship"] == 5
    assert combat.STONE in combat.stats("SEA_TOWER").classes and combat.STONE not in combat.stats("FORTRESS").classes


def test_fortress_arrows_and_garrison():
    assert garrison.arrows("FORTRESS", []) == 5
    assert garrison.arrows("FORTRESS", ["VILLAGER_MALE"] * 3) == 8
    assert garrison.arrows("SEA_TOWER", ["ARCHER"]) == 2
    assert garrison.SIZES["FORTRESS"] == 30


def test_fortress_takes_no_fletching():
    s = combat.stats("FORTRESS")
    assert train.fletching("FORTRESS", s) == s
    assert train.fletching("SEA_TOWER", combat.stats("SEA_TOWER")).range == 9


class Game:
    def __init__(self):
        self.sent = []

    def command(self, cmd):
        self.sent.append(cmd)
        return "Stats: 1 units"


def test_setup_makes_a_target_for_a_fortress_of_the_map():
    data = {"objects": [{"kind": "building", "name": "FORTRESS", "player": 2, "ref": 5, "footprint": [0, 0, 16, 16]}]}
    game = Game()
    combat.setup(game, data)
    uuid = combat.target_uuid([0, 0, 16, 16])
    assert f"aoe arrows {uuid} 5" in game.sent
    assert any(c.startswith(f"aoe building {uuid} 4800 8 11 ") for c in game.sent)
