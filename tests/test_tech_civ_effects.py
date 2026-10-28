"""Civilization bonuses that change the effect of a technology (#2173, AoE2 DE wiki): Bohemian Fervor and Sanctity
also affect the villagers (civs.ALSO), Varangian Bloodlines and Caravan give +50 % effect (civs.MORE)."""
import pytest
from test_train_castle import setup

from game import ai, combat, gather, train


def researched(civ, *techs):
    server, g = setup(civ=civ)
    g.techs.update(techs)
    return server, g


@pytest.mark.parametrize("civ, faster, more", [("BOHEMIANS", 1.15, 15), ("BRITONS", 1.0, 0)])
def test_bohemian_fervor_and_sanctity_affect_the_villagers(civ, faster, more):
    server, g = researched(civ, "FERVOR", "SANCTITY")
    assert train.speed(g, "VILLAGER") == pytest.approx(faster)
    assert train.stats(g, "VILLAGER").hp == combat.stats("VILLAGER").hp + more
    assert train.stats(g, "MONK").hp == combat.stats("MONK").hp + 15 and train.speed(g, "MONK") == pytest.approx(1.15)
    v = gather.Villager("v", (1.5, 64.0, 1.5))
    v.goal = (5, 5)
    server.log.clear()
    g.move(v)                                                         # a villager walk takes the speed of Fervor
    assert server.log[0] == ai.speed_command("v", "VILLAGER", g.map.T, gather.NORMAL * faster)


def test_without_the_technologies_a_bohemian_villager_keeps_its_values():
    server, g = researched("BOHEMIANS")
    assert train.speed(g, "VILLAGER") == 1.0 and train.stats(g, "VILLAGER") == combat.stats("VILLAGER")


@pytest.mark.parametrize("civ, hp, speed", [("VARANGIANS", 30, 1.3), ("BRITONS", 20, 1.2)])
def test_varangian_bloodlines_and_caravan_give_half_more(civ, hp, speed):
    server, g = researched(civ, "BLOODLINES", "CARAVAN")
    assert train.stats(g, "KNIGHT").hp == combat.stats("KNIGHT").hp + hp
    assert train.stats(g, "MILITIA") == combat.stats("MILITIA")        # Bloodlines: only the cavalry
    assert train.speed(g, "TRADE_CART") == pytest.approx(speed)
    assert train.speed(g, "KNIGHT") == 1.0                             # Caravan: only the trade units
