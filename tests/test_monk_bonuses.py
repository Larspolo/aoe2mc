"""The monk bonuses of the Bengalis, Burmese, Teutons and Aztecs (AoE2 DE, #2269): monk armor, half-price monastery
technologies, twice the heal range, and hit points for each monastery technology."""
import pytest

from game import civs, combat, monk, train

from test_civ_work import setup
from test_monk_heal import run, setup as heal_setup


def test_a_bengali_monk_has_3_melee_and_3_pierce_armor():
    s, base = train.stats(setup("BENGALIS"), "MONK"), combat.stats("MONK")
    assert (s.melee, s.pierce) == (base.melee + 3, base.pierce + 3)
    assert train.stats(setup("FRANKS"), "MONK") == base
    assert train.stats(setup("BENGALIS"), "MILITIA") == combat.stats("MILITIA")


def test_burmese_monastery_technologies_cost_half():
    burmese, franks = setup("BURMESE"), setup("FRANKS")
    for t in ("REDEMPTION", "FERVOR"):
        assert {r: int(v / 2 + 0.5) for r, v in train.price(franks, t).items()} == train.price(burmese, t), t
    assert train.price(burmese, "LOOM") == train.price(franks, "LOOM")
    assert train.price(burmese, "MONK") == train.price(franks, "MONK")


@pytest.mark.parametrize("civ, healed", [("TEUTONS", True), ("FRANKS", False)])
def test_a_teutonic_monk_heals_in_twice_the_range(civ, healed):
    server, g = heal_setup(("a", "MILITIA", 1, 5.5 + 7, 10.0, 40.0))     # 7 tiles: out of 4, in 8
    g.data["players"] = {"1": {"civ": civ, "color": 0}}
    assert civs.HEAL_RANGE.get(civ, 1) * monk.RANGE == (8 if healed else 4)
    run(g, 4)
    assert (server.entities["a"]["Health"] > 10.0) == healed


def test_an_aztec_monk_gets_5_hit_points_for_each_monastery_technology():
    g = setup("AZTECS")
    hp = combat.stats("MONK").hp
    assert train.stats(g, "MONK").hp == hp
    g.techs.update({"FERVOR", "SANCTITY", "LOOM"})                   # Loom is not a monastery technology
    assert train.stats(g, "MONK").hp == hp + 2 * 5 + 15             # Sanctity: +15 hit points of its own
    other = setup("FRANKS")
    other.techs.update({"FERVOR", "SANCTITY"})
    assert train.stats(other, "MONK").hp == hp + 15
    assert train.stats(g, "MILITIA").hp == combat.stats("MILITIA").hp
