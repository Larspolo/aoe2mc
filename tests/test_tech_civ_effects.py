"""Civilization bonuses that change the effect of a technology (#2173, AoE2 DE wiki): Bohemian Fervor and Sanctity
also affect the villagers (civs.ALSO), Varangian Bloodlines and Caravan give +50 % effect (civs.MORE)."""
import pytest
from test_train_castle import setup

from game import ai, combat, gather, train


def researched(civ, *techs):
    server, g = setup(civ=civ)
    g.techs.update(techs)
    return server, g


@pytest.mark.parametrize("civ, also", [("BOHEMIANS", True), ("BRITONS", False)])
def test_bohemian_fervor_and_sanctity_affect_the_villagers(civ, also):
    server, g = researched(civ, "FERVOR", "SANCTITY")
    monk, faster = train.stats(g, "MONK").hp - combat.stats("MONK").hp, train.speed(g, "MONK")
    assert monk > 0 and faster > 1
    faster, more = (faster, monk) if also else (1.0, 0)                # the villagers get the effect of the monks
    assert train.speed(g, "VILLAGER") == pytest.approx(faster)
    assert train.stats(g, "VILLAGER").hp == combat.stats("VILLAGER").hp + more
    v = gather.Villager("v", (1.5, 64.0, 1.5))
    v.goal = (5, 5)
    server.log.clear()
    g.move(v)                                                         # a villager walk takes the speed of Fervor
    assert server.log[0] == ai.speed_command("v", "VILLAGER", g.map.T, gather.NORMAL * faster)


def test_without_the_technologies_a_bohemian_villager_keeps_its_values():
    server, g = researched("BOHEMIANS")
    assert train.speed(g, "VILLAGER") == 1.0 and train.stats(g, "VILLAGER") == combat.stats("VILLAGER")


def test_varangian_bloodlines_and_caravan_give_more():
    def effect(civ):
        server, g = researched(civ, "BLOODLINES", "CARAVAN")
        assert train.stats(g, "MILITIA") == combat.stats("MILITIA")    # Bloodlines: only the cavalry
        assert train.speed(g, "KNIGHT") == 1.0                         # Caravan: only the trade units
        return train.stats(g, "KNIGHT").hp - combat.stats("KNIGHT").hp, train.speed(g, "TRADE_CART") - 1
    more, base = effect("VARANGIANS"), effect("BRITONS")
    assert more[0] > base[0] > 0 and more[1] > base[1] > 0
