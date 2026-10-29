"""game/repair.py: selected villagers repair a damaged building of an allied player, as in AoE2 DE (#1361, AoE2 wiki
"Repairing": "While players cannot construct allied buildings, they can repair them"). The own stock pays half the
build cost of the civilization of the ally. A building of an enemy or of no player is not repaired."""
import pytest
from test_gather import grid
from test_repair import HpServer

from game import build, combat, gather, repair

CASTLE, ENEMY, GAIA = (12, 16, 12, 16), (4, 6, 12, 14), (16, 18, 4, 6)   # block footprints (x0, x1, z0, z1)


def setup(stone=400):
    """A flat 24 × 24 map: player 1 (Britons) with a villager "v0"; a damaged castle of the ally 2 (Incas: buildings
    cost less stone); a damaged house of the enemy 3 and of Gaia."""
    objects = [{"kind": "building", "name": "CASTLE", "player": 2, "tile": [14, 14], "footprint": [12, 12, 16, 16]},
               {"kind": "building", "name": "HOUSE", "player": 3, "tile": [5, 13], "footprint": [4, 12, 6, 14]},
               {"kind": "building", "name": "HOUSE", "player": 0, "tile": [17, 5], "footprint": [16, 4, 18, 6]},
               {"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v0", "tile": [10.5, 10.5]}]
    data = grid([[64] * 24 for _ in range(24)], objects)
    data["players"] = {"1": {"civ": "BRITONS", "team": 1}, "2": {"civ": "INCAS", "team": 1},
                       "3": {"civ": "FRANKS", "team": 2}}
    server = HpServer({"v0": {"Pos": (10.5, 64.0, 10.5)}},
                      {repair.uuid(CASTLE): 2400, repair.uuid(ENEMY): 100, repair.uuid(GAIA): 100})
    g = gather.Gather(server, data, start={"stone": stone}).setup()
    g.choose(set(g.villagers), "v0")
    return server, g


def test_a_villager_repairs_an_allied_castle_and_the_own_stock_pays_the_cost_of_the_ally():
    server, g = setup()
    assert repair.owners(g) == {CASTLE: ("CASTLE", 2)}
    ally = repair.cost(g, "CASTLE", 2)
    assert ally == {r: v / 2 for r, v in build.price(g, "CASTLE", 2).items()} != repair.cost(g, "CASTLE")   # Incas
    assert repair.order(g, "Steve", (13, 13)) == CASTLE
    steps = 0
    while g.villagers["v0"].state != "idle" and steps < 3000:
        g.step()
        steps += 1
    full = combat.stats("CASTLE").hp
    assert server.hp[repair.uuid(CASTLE)] == full
    assert abs(400 - g.stock["stone"] - ally["stone"] * (full - 2400) / full) <= 1   # whole stone


@pytest.mark.parametrize("cell", [(4, 12), (16, 4)])
def test_no_repair_of_an_enemy_or_a_gaia_building(cell):
    server, g = setup()
    assert repair.order(g, "Steve", cell) is None and g.villagers["v0"].state == "idle"


def test_a_player_without_a_team_repairs_only_own_buildings():
    server, g = setup()
    del g.players["2"]["team"]
    assert repair.owners(g) == {} and repair.order(g, "Steve", (13, 13)) is None
