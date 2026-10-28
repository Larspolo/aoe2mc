"""A converter stop with a text shows the text in the window (#3052)."""
import numpy as np

import gui


def test_the_text_of_a_stop_is_the_error_text(monkeypatch):
    import aoe2mc

    def stop(args):
        raise SystemExit("A .aoe2record file needs the mgz package: python3 -m pip install mgz")

    monkeypatch.setattr(aoe2mc, "main", stop)
    out = []
    error = gui.convert(["a.aoe2record", "W"], out.append)
    assert error == "A .aoe2record file needs the mgz package: python3 -m pip install mgz"
    assert "needs the mgz package" in "".join(out)


def test_a_record_that_mgz_cannot_read_shows_the_reason(tmp_path):
    bad = tmp_path / "bad.mgz"
    bad.write_bytes(np.random.default_rng(3).integers(0, 256, 4000, dtype=np.uint8).tobytes())
    out = []
    error = gui.convert([str(bad), str(tmp_path / "W")], out.append)
    assert error and "cannot read this recorded game" in error
    assert "cannot read this recorded game" in "".join(out)
