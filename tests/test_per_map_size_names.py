"""game/per.py: the airef map-size names with and without "-map" (#5101)."""
from test_per_setup import script


def test_two_names_of_one_size_both_match(monkeypatch, capsys):
    s, b = script()
    monkeypatch.setitem(b.g.data, "tile_size", 1)
    b.g.data["ground"] = [""] * 120                                    # map_size counts the rows: 120 tiles
    assert s.check(("map-size", "tiny")) and s.check(("map-size", "tiny-map"))
    assert not s.check(("map-size", "large"))
    out = capsys.readouterr()
    assert "unknown" not in out.out + out.err
