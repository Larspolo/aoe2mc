"""The technologies that a civilization gets free in AoE2 DE cost nothing for its player in the game program (#1924,
gap list of #1088; the "Civilization bonuses" of the AoE2 wiki in tests/data/civ_bonuses.jsonl): rules of civs.COSTS."""
import pytest
from test_dock_train import dock_map

from game import train

FREE = {"BYZANTINES": ("TOWN_WATCH", "TOWN_PATROL"), "ETHIOPIANS": ("PIKEMAN_UPGRADE",), "SLAVS": ("ARSON", "GAMBESONS"),
        "TATARS": ("PARTHIAN_TACTICS", "THUMB_RING"), "TEUTONS": ("MURDER_HOLES", "HERBAL_MEDICINE"),
        "THRACIANS": ("ELITE_SKIRMISHER_UPGRADE",), "TURKS": ("CHEMISTRY", "LIGHT_CAVALRY_UPGRADE", "HUSSAR_UPGRADE"),
        "VIETNAMESE": ("CONSCRIPTION",)}


def player(civ):
    _, g = dock_map()
    g.data["players"]["1"]["civ"] = civ
    return g


@pytest.mark.parametrize("civ", sorted(FREE))
def test_each_free_technology_costs_nothing_only_for_its_civilization(civ):
    g, other = player(civ), player("CELTS")                           # the Celts have no cost bonus
    for name in FREE[civ]:
        assert train.COSTS[name] and train.price(g, name) == {}, name
        assert train.price(other, name) == train.COSTS[name], name


def test_the_other_technologies_keep_their_price():
    g = player("TURKS")
    assert train.price(g, "LOOM") == train.COSTS["LOOM"] and train.price(g, "BALLISTICS") == train.COSTS["BALLISTICS"]
