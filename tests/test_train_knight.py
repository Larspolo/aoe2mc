"""game/train.py: the stable trains the knight and the archery range the cavalry archer from the Castle Age, with the
AoE2 DE cost and time of the wiki; before it the item is gray (#1397)."""
import re
from urllib.parse import unquote

import pytest
from test_gather import FakeServer, grid

from game import build, combat, gather, train


def setup(building, ages=("FEUDAL_AGE", "CASTLE_AGE")):
    """A flat 24 × 24 map (tile size 1): a town center of player 1 and a complete building at x 10-12, z 2-4."""
    objects = [{"kind": "building", "name": "TOWN_CENTER", "player": 1, "tile": [3.5, 3.5], "footprint": [2, 2, 5, 5]},
               {"kind": "building", "name": building, "player": 1, "tile": [11.5, 3.5], "footprint": [10, 2, 13, 5]}]
    server = FakeServer({"Steve": {"Pos": (11.5, 64.0, 9.5), "Rotation": (180, 15)}})
    g = gather.Gather(server, grid([[64] * 24 for _ in range(24)], objects), start={}).setup()
    g.stock.update(food=1000, wood=1000, gold=1000)
    g.techs.update(ages)
    return server, g


def menu(server):
    return [unquote(c) for c in server.log if c.startswith("aoe menu ")][-1]


@pytest.mark.parametrize("building, name, label, cost", [
    ("STABLE", "KNIGHT", "Knight", "60 food · 75 gold · 30 s"),
    ("ARCHERY_RANGE", "CAVALRY_ARCHER", "Cavalry Archer", "40 wood · 60 gold · 37 s"),
])
def test_the_castle_age_menu_has_the_unit_with_its_cost(building, name, label, cost):
    server, g = setup(building)
    train.open_menu(g, "Steve", (11, 3))
    assert f"{train.ITEMS[name][0]}:{train.ITEMS[name][1]}:{label}:{cost} · queue 0/15 " in menu(server)
    assert train.ITEMS[name][1] in ("horse_spawn_egg", "skeleton_horse_spawn_egg")


@pytest.mark.parametrize("building, label, slot", [("STABLE", "Knight", 3), ("ARCHERY_RANGE", "Cavalry Archer", 4)])
def test_the_unit_is_gray_before_the_castle_age(building, label, slot):
    server, g = setup(building, ages=("FEUDAL_AGE",))
    train.open_menu(g, "Steve", (11, 3))
    assert re.search(f"{slot}:gray_dye:{label}:[^ ]* .* Needs the Castle Age", menu(server))
    rect = train.home(g, (11, 3))
    assert train.order(g, "Steve", rect, slot) == 0 and g.stock == {"food": 1000, "wood": 1000, "gold": 1000, "stone": 0}


@pytest.mark.parametrize("building, name, mount, rider", [
    ("STABLE", "KNIGHT", "horse", "zombie"),
    ("ARCHERY_RANGE", "CAVALRY_ARCHER", "skeleton_horse", "skeleton"),
])
def test_a_trained_unit_is_a_rider_with_its_aoe2_values(building, name, mount, rider):
    server, g = setup(building)
    rect = train.open_menu(g, "Steve", (11, 3))
    assert train.order(g, "Steve", rect, train.ITEMS[name][0]) == 1 and g.queues[rect][0]["name"] == name
    assert train.tick(g, train.TRAIN_TIMES[name] - 1) == []
    uuid, = train.tick(g, 1)
    summon, = [c for c in server.log if c.startswith("summon")]
    flat = re.sub(r"\s", "", summon)
    assert summon.startswith(f"summon minecraft:{mount} ") and f"Passengers:[{{id:\"minecraft:{rider}\"" in flat
    assert g.soldiers == {uuid: name}
    s = combat.STATS[name]
    assert "cavalry" in s.classes and (s.hp, s.range > 0) == {"KNIGHT": (100, False), "CAVALRY_ARCHER": (50, True)}[name]


def test_each_menu_slot_of_a_building_has_one_item():
    """Two items in one slot: a click orders only the first one."""
    for building, names in train.TRAINS.items():
        slots = [train.ITEMS[n][0] for n in names if train.AFTER.get(n) not in names]   # AFTER: the slot of the one before
        assert len(slots) == len(set(slots)), building


def test_the_units_are_of_the_castle_age():
    assert build.AGE["KNIGHT"] == build.AGE["CAVALRY_ARCHER"] == 2
