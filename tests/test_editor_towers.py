"""The Sea Tower and the Fortress of the Scenario Editor take hits and shoot (AoE2 wiki, #2137)."""
from game import combat, garrison, train


def test_fortress_arrows_and_garrison():
    base = garrison.arrows("FORTRESS", [])
    assert base > 0 and garrison.arrows("FORTRESS", ["VILLAGER_MALE"] * 3) == base + 3
    assert garrison.arrows("SEA_TOWER", ["ARCHER"]) == garrison.arrows("SEA_TOWER", []) + 1


def test_fortress_takes_no_fletching():
    s = combat.stats("FORTRESS")
    assert train.fletching("FORTRESS", s) == s
    assert train.fletching("SEA_TOWER", combat.stats("SEA_TOWER")).range > combat.stats("SEA_TOWER").range


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
    s = combat.stats("FORTRESS")
    assert f"aoe arrows {uuid} {garrison.arrows('FORTRESS', [])}" in game.sent
    assert any(c.startswith(f"aoe building {uuid} {s.hp} {s.melee} {s.pierce} ") for c in game.sent)
