"""tools/measure_convert.py without /proc, as on macOS (#1043): rss() falls back to resource.getrusage."""
import measure_convert
import scenarios


def test_rss_without_proc_gives_the_peak(monkeypatch):
    monkeypatch.setattr(measure_convert, "STATM", "/nonexistent/statm")
    assert 10 * 2**20 < measure_convert.rss() < 16 * 2**30


def test_each_phase_has_a_peak_without_proc(tmp_path, monkeypatch):
    monkeypatch.setattr(measure_convert, "STATM", "/nonexistent/statm")
    src = scenarios.tiny(str(tmp_path / "tiny.aoe2scenario"))
    secs, peak, total, text = measure_convert.measure(src, str(tmp_path / "W"))
    assert list(secs) == ["read", "columns", "objects", "units", "chunks", "write"]
    assert all(m > 10 * 2**20 for m in peak.values())
    assert list(peak.values()) == sorted(peak.values())             # the peak up to now never falls
