"""game/train.py: a Mapuche player researches the upgrades of the spearman and skirmisher lines also at its Settlement,
in the time of the barracks and the archery range (#2487, AoE2 DE wiki "Settlement (Age of Empires II)": "They can also
be upgraded there in the same time as at their regular production buildings")."""
import pytest
from test_folwark import complete, polish
from test_settlement_bonuses import age

from game import civs, train


def test_the_upgrades_have_one_slot_per_line_after_the_units():
    spear, skirm = (train.slots("SETTLEMENT", n)[0] for n in ("SPEARMAN", "SKIRMISHER"))
    pike, halb, elite = (train.slots("SETTLEMENT", n)[0] for n in ("PIKEMAN_UPGRADE", "HALBERDIER_UPGRADE",
                                                                   "ELITE_SKIRMISHER_UPGRADE"))
    assert (pike, halb, elite) == (skirm + 1, skirm + 1, skirm + 2)
    assert train.slots("BARRACKS", "PIKEMAN_UPGRADE") == train.ITEMS["PIKEMAN_UPGRADE"]   # the barracks: no change


def test_a_mapuche_settlement_researches_pikeman_in_the_barracks_time():
    server, g = polish("MAPUCHE")
    age(g, 2)
    assert {"PIKEMAN_UPGRADE", "ELITE_SKIRMISHER_UPGRADE"} <= set(train.trains(g, "SETTLEMENT"))
    time = train.seconds(g, "PIKEMAN_UPGRADE", "SETTLEMENT")
    assert time == pytest.approx(train.seconds(g, "PIKEMAN_UPGRADE", "BARRACKS"))
    server.entities["sp"] = {"Pos": (40.5, 64.0, 40.5)}
    g.soldiers["sp"] = "SPEARMAN"
    g.stock.update(food=1000, gold=1000)
    x0, _, z0, _ = complete(g, "SETTLEMENT", 20, 20)["footprint"]
    assert train.queue(g, "Steve", (x0 + 1, z0 + 1), "PIKEMAN_UPGRADE")
    train.tick(g, time - 1)
    assert "PIKEMAN_UPGRADE" not in g.techs
    train.tick(g, 1.5)
    assert "PIKEMAN_UPGRADE" in g.techs and g.soldiers["sp"] == "PIKEMAN"


def test_other_civilizations_research_no_upgrades_at_a_settlement():
    server, g = polish(next(r["name"] for r in civs.ROWS if "SETTLEMENT" not in civs.TRAINS.get(r["name"], {})))
    age(g, 3)
    assert not {"PIKEMAN_UPGRADE", "ELITE_SKIRMISHER_UPGRADE"} & set(train.trains(g, "SETTLEMENT"))
