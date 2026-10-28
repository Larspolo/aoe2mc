"""game/gather.py: a villager at a shore fish gathers at the AoE2 fish rate, 0.43 food per game second (AoE2 DE wiki
"Fishing", #1283), not at the forage rate with its civilization bonus (#2349), and a right click sends it there."""
import pytest
from test_drop_bonus import game
from test_ship_gather import fish_map

from game import fleet, gather


def fished(civ, seconds=20):
    """The food that a villager of civ gathers at a shore fish in `seconds` real seconds (a large load)."""
    g = game(civ)
    g.carry = 1000
    g.map.fish[(5, 5)] = 1000
    v = g.villagers["v"] = gather.Villager("v", (5.5, 64.0, 6.5))
    v.state, v.res, v.load, v.tree, v.path, v.timer = "chop", "food", 0, (5, 5), [], 0.0
    for _ in range(round(seconds / g.tick)):
        g.step()
    assert v.state == "chop"
    return v.load


@pytest.mark.parametrize("civ", ["BRITONS", "FRANKS"])                 # Franks: foragers +15 %, not fishermen
def test_a_villager_fishes_at_the_aoe2_fish_rate(civ):
    assert fished(civ) == int(20 * gather.NORMAL * gather.AOE2_WORK["fish"])   # 0.43 food per game second


def test_a_right_click_at_a_shore_fish_sends_the_selected_villager():
    server, g, _ = fish_map()
    v = g.villagers["v"] = gather.Villager("v", (10.5, 64.0, 6.5))
    g.select("v")
    eye = (13.5, 65.62, 3.5)
    d = next(gather.direction(-90, p / 2) for p in range(2, 180)
             if (c := fleet.pick(g, eye, gather.direction(-90, p / 2))) and c == (14, 3))
    assert g.shore_fish(eye, d) == (14, 3)
    g.looks["Steve"] = eye, d
    g.click("Steve")
    assert v.tree == (14, 3) and v.res == "food"
    far = next(gather.direction(-90, p / 2) for p in range(2, 80)
               if (c := fleet.pick(g, (12.5, 65.62, 12.5), gather.direction(-90, p / 2))) and c == (20, 12))
    assert g.shore_fish((12.5, 65.62, 12.5), far) is None              # a deep fish: only the fishing ships


def test_an_empty_shore_fish_goes_and_the_villager_takes_the_food_home():
    g = game("BRITONS")
    g.map.fish[(5, 5)], g.map.fish_mobs[(5, 5)] = 3, "salmon"
    g.map.shore.add((5, 5))
    v = g.villagers["v"] = gather.Villager("v", (5.5, 64.0, 6.5))
    v.state, v.res, v.load, v.tree, v.path, v.timer = "chop", "food", 0, (5, 5), [], 0.0
    for _ in range(40):
        g.step()
        if v.state != "chop":
            break
    assert (5, 5) not in g.map.fish and (5, 5) not in g.map.shore
    assert any(c.startswith("kill @e[type=minecraft:salmon") for c in g.game.log)   # the fish mob
    assert v.load == 3 and v.state == "to_drop"
