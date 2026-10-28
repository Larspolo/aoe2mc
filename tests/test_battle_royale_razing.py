"""The town centers that the Battle Royale start removes give no razing and no loot (#3113): the start frees their
footprints with Gather.free and does not add them to the sieged targets, so Gather.fall does not see them (#3005)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import battle_royale  # noqa: E402
import combat  # noqa: E402
import gather  # noqa: E402
from test_gather import FakeServer, grid  # noqa: E402

TOWNS = {1: [4, 4, 8, 8], 2: [20, 4, 24, 8], 3: [4, 20, 8, 24]}


def town_game(civ):
    data = grid([[64] * 32 for _ in range(32)], [])
    data["objects"] = [dict(kind="building", name="TOWN_CENTER", player=p, footprint=fp) for p, fp in TOWNS.items()]
    data["players"] = {"1": {"civ": civ}}
    g = gather.Gather(FakeServer({}), data, resources="high").setup()
    for p, fp in TOWNS.items():                                       # the footprints the Gather has (its forts)
        x0, z0, x1, z1 = fp
        g.forts[combat.target_uuid(fp)] = (x0, 64, z0, x1, 70, z1)
        g.map.blocked.update((x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1))
    return g


def test_a_removed_town_center_gives_no_razing():
    g = town_game("BRITONS")
    battle_royale.start(g)
    g.fall()
    assert vars(g).get("razed", {}) == {}                             # score.razed sets it only for a razing
    assert not any(u in g.sieged for u in (combat.target_uuid(fp) for fp in TOWNS.values()))


def test_a_danish_player_gets_no_loot_for_a_removed_town_center():
    g = town_game("DANES")
    wood = g.stock["wood"]
    battle_royale.start(g)
    g.fall()
    assert g.stock["wood"] == wood and g.stock["stone"] == 0


def test_the_footprints_of_the_removed_town_centers_are_free():
    g = town_game("BRITONS")
    battle_royale.start(g)
    assert all(g.map.free(x, z) for x in range(20, 25) for z in range(4, 9))   # the town of player 2
    assert not any(combat.target_uuid(fp) in g.forts for fp in TOWNS.values())
