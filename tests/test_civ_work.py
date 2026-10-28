"""game/civs.py: the villagers of a player work at the rate of the own civilization (AoE2 DE bonuses, #1089)."""
import pytest

from game import civs, gather, train

from test_gather import FakeServer, grid
from test_gather_hunt import game as hunt_game


def setup(civ):
    """A flat 16 × 16 map with a villager of player 1, whose civilization is civ."""
    objects = [{"kind": "unit", "name": "VILLAGER_MALE", "player": 1, "uuid": "v", "tile": [7.5, 7.5]}]
    data = grid([[64] * 16 for _ in range(16)], objects)
    data["players"] = {"1": {"civ": civ, "color": 0}}
    return gather.Gather(FakeServer({"v": {"Pos": (7.5, 64.0, 7.5)}}), data).setup()


def test_celts_chop_wood_15_percent_faster():
    base, g = setup("GOTHS"), setup("CELTS")
    assert civs.civ(g) == "CELTS" and g.work_time("wood") == pytest.approx(base.work_time("wood") / 1.15)
    assert all(g.work_time(r) == base.work_time(r) for r in ("food", "farm", "gold", "stone", "hunt"))


def test_franks_forage_15_percent_faster():
    base, g = setup("GOTHS"), setup("FRANKS")
    assert g.work_time("food") == pytest.approx(base.work_time("food") / 1.15)
    assert g.work_time("farm") == base.work_time("farm") and g.work_time("wood") == base.work_time("wood")


def test_a_civilization_with_no_bonus_works_at_the_aoe2_rate():
    g = setup("GOTHS")
    assert civs.civ(g) == "GOTHS" and "GOTHS" not in civs.WORK
    assert all(g.work_time(r) == pytest.approx(gather.WORK_SECONDS[r]) for r in gather.WORK_SECONDS)


def test_britons_shepherds_and_mongol_hunters():
    base, britons, mongols = setup("GOTHS"), setup("BRITONS"), setup("MONGOLS")
    assert britons.work_time("hunt", herd=True) == pytest.approx(base.work_time("hunt") / 1.25)
    assert britons.work_time("hunt") == base.work_time("hunt")         # a deer: no shepherd bonus
    assert mongols.work_time("hunt") == pytest.approx(base.work_time("hunt") / 1.4)
    assert mongols.work_time("hunt", herd=True) == base.work_time("hunt")


def test_the_bonus_multiplies_with_the_technologies():
    base, g = setup("CELTS"), setup("CELTS")
    g.techs.add("DOUBLE_BIT_AXE")
    assert g.work_time("wood") == pytest.approx(base.work_time("wood") / 1.2)


def test_a_sheep_carcass_is_a_herd_and_a_deer_carcass_not():
    for animal, player, herd in (("SHEEP", 1, True), ("DEER", 0, False)):
        _, g = hunt_game(animal, player, aegis=True)
        g.hunt("a")
        for _ in range(400):
            g.step()
            if g.map.carcasses:
                break
        assert list(g.map.carcasses) == [(8, 2)] and ((8, 2) in g.map.herds) == herd


def test_the_castle_reads_the_civilization_with_civ():
    g = setup("CELTS")
    techs = tuple(n for n, c in train.BY_KEY["civ"].items() if c == "CELTS")          # the unique technologies (#2021, #2043)
    assert train.trains(g, "CASTLE") == tuple(n for n in [train.UNIQUE.get("CELTS")] if n in train.COSTS) + train.TRAINS["CASTLE"] + techs


def test_each_entry_is_a_known_civilization_and_kind():
    import buildings
    known = {c for v in buildings.CIV_ARCH.values() for c in v.split()}
    kinds = {"farm", "food", "gold", "hunt", "oyster", "sheep", "stone", "wood"}
    assert set(civs.WORK) <= known and all(set(w) <= kinds for w in civs.WORK.values())
    assert list(civs.WORK) == sorted(civs.WORK)
