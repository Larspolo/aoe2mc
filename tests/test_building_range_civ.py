"""The civilization key "building_range" (#4450): a building of the civilization shoots from more tiles (Antiquity
Mode: the Choson towers have +2 range). Test data: a civilization line of the test, not the data file."""
from game import civs, combat

BOX = (0, 64, 0, 3, 66, 3)


def test_building_range_adds_tiles(monkeypatch):
    monkeypatch.setattr(civs, "BUILDING_RANGE", {"TESTCIV": {"WATCH_TOWER": 2}})
    base = combat.stats("WATCH_TOWER")
    s = civs.hp("TESTCIV", "WATCH_TOWER", base)
    assert s.range == base.range + 2 and s.hp == base.hp
    assert civs.hp("OTHER", "WATCH_TOWER", base) == base
    assert civs.hp("TESTCIV", "CASTLE", combat.stats("CASTLE")) == combat.stats("CASTLE")


def test_building_range_in_shoot_command(monkeypatch):
    monkeypatch.setattr(civs, "BUILDING_RANGE", {"TESTCIV": {"WATCH_TOWER": 2}})
    base = combat.stats("WATCH_TOWER")
    far = combat.building(combat.target_uuid([0, 0, 0, 0]), "WATCH_TOWER", 1, BOX, T=4, s=civs.hp("TESTCIV", "WATCH_TOWER", base))
    near = combat.building(combat.target_uuid([0, 0, 0, 0]), "WATCH_TOWER", 1, BOX, T=4, s=civs.hp("OTHER", "WATCH_TOWER", base))
    assert far != near
    assert any(f" {base.range * 4 + 8} " in c for c in far) and not any(f" {base.range * 4 + 8} " in c for c in near)
