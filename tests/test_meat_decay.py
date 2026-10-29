"""#2310: the food of a carcass decays at the AoE2 rate (not for the Jurchens), and Magyar villagers kill predators in
one strike."""
import math

import pytest

from game import civs, gather

from test_gather import grid
from test_gather_hunt import Hunt


def game(animal, civ, hp=20.0):
    """A villager of player 1 (civilization civ) next to the animal, tile size 1."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [6.5, 2.5]},
               {"kind": "unit", "name": animal, "player": 0, "uuid": "a", "tile": [8.5, 2.5]},
               {"kind": "building", "name": "TOWN_CENTER", "player": 1, "footprint": [2, 8, 6, 12]}]
    server = Hunt({"v": {"Pos": (7.5, 64.0, 2.5)}, "a": {"Pos": (8.5, 64.0, 2.5), "Health": hp}})
    data = grid([[64] * 16 for _ in range(16)], objects)
    data["players"] = {"1": {"civ": civ}}
    g = gather.Gather(server, data, tick=0.25, carry=10, start={}).setup()
    g.select("v")
    return server, g


def kill(server, g):
    """Hunt the animal until it is dead; return the damage commands."""
    g.hunt("a")
    for _ in range(400):
        if g.villagers["v"].prey is None:                            # the next strike after the death makes the carcass
            break
        g.step()
    return [c for c in server.log if c.startswith("damage a ")]


@pytest.mark.parametrize("animal", ["DEER", "WILD_BOAR", "SHEEP"])
def test_a_carcass_with_no_hunter_loses_food_at_the_aoe2_rate(animal):
    server, g = game(animal, "BRITONS")
    rate = gather.DECAY[animal] * civs.decay(g)
    kill(server, g)
    g.villagers["v"].state = "idle"                                  # nobody gathers it
    tile, = g.map.carcasses
    food = g.map.carcasses[tile]
    g.decay(100.0)                                                   # 100 game seconds
    assert g.map.carcasses[tile] == pytest.approx(food - 100 * rate)
    g.decay(10000.0)
    assert g.map.carcasses[tile] == 0 and tile not in g.map.rot     # it ends at 0


def test_the_steps_decay_in_game_seconds():
    server, g = game("DEER", "FRANKS")
    kill(server, g)
    tile, = g.map.carcasses
    g.villagers["v"].state = "idle"
    food = g.map.carcasses[tile]
    for _ in range(40):                                              # 10 real seconds
        g.step()
    assert g.map.carcasses[tile] == pytest.approx(food - 10 * gather.NORMAL * gather.DECAY["DEER"] * civs.decay(g))


def test_a_jurchen_carcass_keeps_its_food():
    server, g = game("DEER", "JURCHENS")
    kill(server, g)
    tile, = g.map.carcasses
    food = g.map.carcasses[tile]
    g.decay(100.0)                                                   # the civilization factor of the decay
    assert g.map.carcasses[tile] == pytest.approx(food - 100 * gather.DECAY["DEER"] * civs.decay(g))
    assert food == gather.HUNT_FOOD["DEER"]


def test_a_magyar_villager_kills_a_wolf_with_one_strike():
    server, g = game("WOLF", "MAGYARS", hp=8.0)                      # the vanilla health of a wolf
    assert "a" in g.prey and gather.predator("WOLF") and not gather.predator("DEER")
    hit = gather.VILLAGER_HIT[0] + civs.predator_hit(g)
    assert hit > gather.VILLAGER_HIT[0]
    assert kill(server, g) == [f"damage a {hit} minecraft:mob_attack by v"] * math.ceil(8 / hit)
    assert g.map.carcasses == {} and g.villagers["v"].state == "idle"   # a wolf has no food


def test_another_villager_needs_more_strikes_for_a_wolf():
    server, g = game("WOLF", "BRITONS", hp=8.0)
    hit = gather.VILLAGER_HIT[0]
    assert kill(server, g) == [f"damage a {hit} minecraft:mob_attack by v"] * math.ceil(8 / hit)
    assert "a" not in server.entities


def test_the_bonus_is_only_against_predators():
    server, g = game("DEER", "MAGYARS")
    assert set(kill(server, g)) == {f"damage a {gather.VILLAGER_HIT[0]} minecraft:mob_attack by v"}
