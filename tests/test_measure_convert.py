"""tools/measure_convert.py: the time and peak memory of each conversion phase (#690), and the `large` scenario."""
import measure_convert
import scenarios


def test_each_phase_has_its_time_and_peak_memory(tmp_path):
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    secs, peak, total, text = measure_convert.measure(src, str(tmp_path / "W"))
    assert list(secs) == ["read", "columns", "objects", "units", "chunks", "write"]
    assert abs(sum(secs.values()) - total) < 1e-6 and "units in a block (moved up): 0" in text
    assert all(10 * 2**20 < m < 4 * 2**30 for m in peak.values())    # RSS of this process: more than 10 MB
    out = measure_convert.table(secs, peak, total)
    assert out.startswith("| Phase | Seconds |") and "| total |" in out and "Slowest phase: " in out


def test_the_large_maker_is_registered():
    assert scenarios.MAKERS["large"] is scenarios.large


def test_a_small_large_map_has_towns_forests_and_water(tmp_path):
    import aoe2mc
    size, terrain, elevation, tnames, texts, objects, players = aoe2mc.read_map(
        scenarios.large(str(tmp_path / "l.aoe2scenario"), size=96, players=2))
    names = [o["name"] for o in objects]
    assert size == 96 and names.count("TOWN_CENTER") == 2 and names.count("VILLAGER_MALE") == 40
    assert names.count("TREE_OAK_FOREST") > 100 and elevation.max() >= 2
