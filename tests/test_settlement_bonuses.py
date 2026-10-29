"""The Settlement bonuses of three civilizations (#2432, epic #1088, AoE2 DE wiki "Civilization bonuses"). The tests
take the factors and amounts from game/data/civs.jsonl:
- Mapuche: Settlements train the spearman and skirmisher lines in a factor of the time of the barracks and the archery
  range in each age (train.trains, train.slots, train.seconds).
- Muisca: Settlements cost less and heal the allied human units near them by the hit points per AoE2 minute of the
  age (regen.aura).
- Tupi: villagers garrison in a Settlement (garrison.size)."""
import pytest
from test_folwark import complete, polish
from test_gather import grid
from test_monk_heal import HealServer

from game import build, civs, garrison, gather, regen, train

AGES = ("FEUDAL_AGE", "CASTLE_AGE", "IMPERIAL_AGE")
LINES = {n for line in civs.TRAINS["MAPUCHE"]["SETTLEMENT"]["lines"] for n in line}   # the units of the Mapuche lines


def other(table):
    """A civilization with no Settlement entry in the civs table."""
    return next(r["name"] for r in civs.ROWS if "SETTLEMENT" not in table.get(r["name"], {}))


def age(g, n):
    for t in AGES[:n]:
        train.research(g, {"name": t}, start=True)


@pytest.mark.parametrize("ages", [1, 2, 3])
def test_a_mapuche_settlement_trains_spearmen_and_skirmishers_in_the_factor_of_the_age(ages):
    factor = civs.TRAINS["MAPUCHE"]["SETTLEMENT"]["time"][ages]
    server, g = polish("MAPUCHE")
    age(g, ages)
    for unit, building in (("SPEARMAN", "BARRACKS"), ("SKIRMISHER", "ARCHERY_RANGE")):
        assert unit in train.trains(g, "SETTLEMENT")
        assert train.seconds(g, unit, "SETTLEMENT") == pytest.approx(train.seconds(g, unit, building) * factor)
    assert train.seconds(g, "DOUBLE_BIT_AXE", "SETTLEMENT") == train.seconds(g, "DOUBLE_BIT_AXE", "LUMBER_CAMP")


def test_the_two_lines_have_their_own_slots_after_the_technologies_and_a_villager_queues_a_spearman():
    server, g = polish("MAPUCHE")
    age(g, 1)
    techs = {train.slots("SETTLEMENT", n)[0] for n in train.TRAINS["SETTLEMENT"]}
    spear, skirm = (train.slots("SETTLEMENT", n)[0] for n in ("SPEARMAN", "SKIRMISHER"))
    assert spear == max(techs) + 1 and skirm == spear + 1
    assert train.slots("SETTLEMENT", "PIKEMAN")[0] == spear
    assert train.slots("BARRACKS", "SPEARMAN") == train.ITEMS["SPEARMAN"]   # the barracks: no change
    g.stock.update(food=1000)
    site = complete(g, "SETTLEMENT", 20, 20)
    x0, _, z0, _ = site["footprint"]
    assert train.queue(g, "Steve", (x0 + 1, z0 + 1), "SPEARMAN")


def test_other_civilizations_train_no_units_at_a_settlement():
    server, g = polish(other(civs.TRAINS))
    age(g, 3)
    assert not LINES & set(train.trains(g, "SETTLEMENT"))


def test_a_muisca_settlement_costs_less():
    tupi = build.price(polish("TUPI")[1], "SETTLEMENT")
    assert tupi == build.COSTS["SETTLEMENT"]
    assert all(v < tupi[r] for r, v in build.price(polish("MUISCA")[1], "SETTLEMENT").items())


def heal_map(civ):
    """A flat 40 × 40 map (tile size 1): a complete Settlement of player 1 of civ at blocks 10..12, an injured villager
    and militia within 3 tiles, an injured militia 5 tiles away, an injured scout cavalry and an enemy militia nearby."""
    units = (("v", "VILLAGER_MALE", 1, 14.5), ("m", "MILITIA", 1, 15.5), ("far", "MILITIA", 1, 18.5),
             ("s", "SCOUT_CAVALRY", 1, 14.5), ("foe", "MILITIA", 2, 14.5))
    objects = [{"kind": "unit", "name": n, "player": p, "uuid": u, "tile": [x, 11.5]} for u, n, p, x in units]
    objects.append({"kind": "building", "name": "SETTLEMENT", "player": 1, "footprint": [10, 10, 13, 13]})
    server = HealServer({u: {"Pos": (x, 64.0, 11.5), "Health": 10.0, "Max": 40.0} for u, _, _, x in units})
    data = grid([[64] * 40 for _ in range(40)], objects)
    data["players"] = {"1": {"civ": civ}, "2": {"civ": "BRITONS"}}
    g = gather.Gather(server, data).setup()
    g.villagers.setdefault("v", None)
    return server, g


@pytest.mark.parametrize("ages", [0, 1, 2, 3])
def test_a_muisca_settlement_heals_allied_human_units_within_3_tiles(ages):
    rate = civs.HEAL_AURA["MUISCA"]["SETTLEMENT"]["rate"][ages]
    server, g = heal_map("MUISCA")
    age(g, ages)
    regen.tick(g, 60.0)                                                # one AoE2 minute
    hp = {u: e["Health"] for u, e in server.entities.items()}
    assert hp["v"] == hp["m"] == pytest.approx(10.0 + rate)
    assert hp["far"] == hp["s"] == hp["foe"] == 10.0                   # 5 tiles away, the scout line, an enemy


def test_another_civilization_has_no_heal_aura():
    server, g = heal_map(other(civs.HEAL_AURA))
    regen.tick(g, 60.0)
    assert all(e["Health"] == 10.0 for e in server.entities.values())


def test_a_tupi_settlement_takes_villagers():
    assert garrison.size(polish("TUPI")[1], "SETTLEMENT") == civs.GARRISON["TUPI"]["SETTLEMENT"]
    assert garrison.size(polish(other(civs.GARRISON))[1], "SETTLEMENT") == garrison.SIZES.get("SETTLEMENT", 0)
