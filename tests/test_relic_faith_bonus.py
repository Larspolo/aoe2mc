"""game/monk.py and game/civs.py: each relic in an own monastery gives +1 attack to the Lithuanian knights and Leitis,
at most +4, and Muisca monks regain faith 100 % faster after a conversion (AoE2 DE wiki, #2314). Fake server."""
import pytest
import test_monk_convert
import test_relics

from game import combat, monk, train

HOME = (14, 18, 2, 6)


def relic_world(civ, n):
    """The world of test_relics with a knight "k" and n relics in the own monastery, the player of civilization civ."""
    server, g = test_relics.setup()
    g.data["players"] = {"1": {"civ": civ}}
    g.soldiers["k"] = "KNIGHT"
    g.relics += [{"at": None, "monk": None, "home": None} for _ in range(n - len(g.relics))]
    for r in g.relics[:n]:
        r.update(at=None, home=HOME)
    return server, g


@pytest.mark.parametrize("n, more", [(1, 1), (3, 3), (6, 4)])
def test_a_lithuanian_knight_has_1_attack_per_relic_at_most_4(n, more):
    server, g = relic_world("LITHUANIANS", n)
    assert train.stats(g, "KNIGHT").attack == combat.stats("KNIGHT").attack + more
    assert train.stats(g, "LEITIS").attack == combat.stats("LEITIS").attack + more
    assert train.stats(g, "MAN_AT_ARMS").attack == combat.stats("MAN_AT_ARMS").attack
    monk.relic_tick(g, monk.EVERY)                                     # the live knight gets the new attack
    assert combat.stats_command("k", "KNIGHT", train.stats(g, "KNIGHT")) in server.log


def test_no_relic_attack_for_another_civilization_or_without_a_relic():
    server, g = relic_world("FRANKS", 2)
    assert train.stats(g, "KNIGHT").attack == combat.stats("KNIGHT").attack
    server, g = relic_world("LITHUANIANS", 0)
    assert train.stats(g, "KNIGHT").attack == combat.stats("KNIGHT").attack


@pytest.mark.parametrize("civ, rest", [("MUISCA", monk.REST / 2), ("AZTECS", monk.REST)])
def test_a_muisca_monk_converts_again_in_half_the_time(civ, rest):
    server, g = test_monk_convert.setup(("a", "MILITIA", 2, 8.5), ("b", "MILITIA", 2, 9.5))
    g.data["players"] = {"1": {"civ": civ}}
    monk.convert_order(g, {"monk"}, "a")
    test_monk_convert.until_converted(g, "a")
    assert g.faith["monk"] == pytest.approx(rest)
    monk.convert_order(g, {"monk"}, "b")
    assert test_monk_convert.until_converted(g, "b", limit=rest - 1) == pytest.approx(rest - 1)
    assert test_monk_convert.until_converted(g, "b") <= 1 + 9 * monk.INTERVAL
