"""tools/dat_compare.py: compare() drops the lines of ACCEPTED (name and key) and keeps the other keys (#5305).
Test objects only: the gather rates are patched, no .dat is read."""
from tools import dat_compare as dc


def patch_rates(monkeypatch, accepted):
    monkeypatch.setattr(dc, "GATHERERS", {"farm": 1, "wood": 2})
    monkeypatch.setattr(dc, "base_unit", lambda dat, uid: uid)
    monkeypatch.setattr(dc, "work_rate", lambda u: 0.1)
    monkeypatch.setitem(dc.ACCEPTED, ("AOE2_WORK", "farm"), "test")
    for name, key in accepted:
        monkeypatch.setitem(dc.ACCEPTED, (name, key), "test")


def test_an_accepted_name_and_key_give_no_line(monkeypatch):
    patch_rates(monkeypatch, [("AOE2_WORK", "wood")])
    assert dc.compare(None, {}, {}, {"AOE2_WORK": {"farm": 0.5, "wood": 0.5}}) == []


def test_another_key_of_the_same_name_gives_its_line(monkeypatch):
    patch_rates(monkeypatch, [("AOE2_WORK", "wood")])
    out = dc.compare(None, {}, {}, {"AOE2_WORK": {"farm": 0.5, "wood": 0.5, "stone": 0.5}})
    assert out == []                                   # stone has no GATHERERS entry: no line either way
    monkeypatch.setitem(dc.GATHERERS, "stone", 3)
    out = dc.compare(None, {}, {}, {"AOE2_WORK": {"farm": 0.5, "wood": 0.5, "stone": 0.5}})
    assert out == ["AOE2_WORK stone: 0.5, 0.1"]


def test_accepted_is_by_name_and_key_of_the_line():
    assert dc.accepted("AOE2_WORK farm: 0.5, 0.33")
    assert not dc.accepted("AOE2_WORK wood: 0.5, 0.33")
    assert not dc.accepted("AOE2_WORK: no rate")
