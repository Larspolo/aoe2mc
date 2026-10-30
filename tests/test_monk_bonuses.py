"""The monk bonuses of the Bengalis, Burmese, Teutons and Aztecs (AoE2 DE, #2269): monk armor, half-price monastery
technologies, twice the heal range, and hit points for each monastery technology. The values come from the data:
the tests compare with a civilization without the bonus."""
import pytest
from test_civ_work import setup
from test_monk_heal import run
from test_monk_heal import setup as heal_setup

from game import civs, combat, monk, train


def test_a_bengali_monk_has_more_melee_and_pierce_armor():
    s, base = train.stats(setup("BENGALIS"), "MONK"), combat.stats("MONK")
    assert s.melee > base.melee and s.pierce > base.pierce
    assert train.stats(setup("FRANKS"), "MONK") == base
    assert train.stats(setup("BENGALIS"), "MILITIA") == combat.stats("MILITIA")


def test_burmese_monastery_technologies_cost_less():
    burmese, franks = setup("BURMESE"), setup("FRANKS")
    for t in ("REDEMPTION", "FERVOR"):
        cheap, full = train.price(burmese, t), train.price(franks, t)
        assert set(cheap) == set(full) and all(cheap[r] < v for r, v in full.items()), t
    assert train.price(burmese, "LOOM") == train.price(franks, "LOOM")
    assert train.price(burmese, "MONK") == train.price(franks, "MONK")


@pytest.mark.parametrize("civ", ["TEUTONS", "FRANKS"])
def test_a_teutonic_monk_heals_in_its_heal_range(civ):
    server, g = heal_setup(("a", "MILITIA", 1, 5.5 + monk.RANGE + 1, 10.0, 40.0))   # out of the normal range
    g.data["players"] = {"1": {"civ": civ, "color": 0}}
    run(g, 4)
    assert (server.entities["a"]["Health"] > 10.0) == (civs.HEAL_RANGE.get(civ, 1) * monk.RANGE >= monk.RANGE + 1)


def test_an_aztec_monk_gets_hit_points_for_each_monastery_technology():
    g = setup("AZTECS")
    hp, per = combat.stats("MONK").hp, civs.TECH_HP["AZTECS"][0][2]
    assert train.stats(g, "MONK").hp == hp
    g.techs.update({"FERVOR", "SANCTITY", "LOOM"})                   # Loom is not a monastery technology
    other = setup("FRANKS")
    other.techs.update({"FERVOR", "SANCTITY", "LOOM"})
    assert train.stats(g, "MONK").hp == train.stats(other, "MONK").hp + 2 * per
    assert train.stats(g, "MILITIA").hp == combat.stats("MILITIA").hp
