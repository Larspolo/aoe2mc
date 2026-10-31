"""A base scenario of DE (.scx of format 1.33 and later) goes to read_scenario (#4933)."""
import shutil

import pytest

import aoe2mc


@pytest.fixture
def de_scx(tmp_path):
    import subprocess
    import sys
    src = tmp_path / "t.aoe2scenario"
    subprocess.run([sys.executable, "tools/scenarios.py", "tiny", str(src)], check=True, capture_output=True,
                   cwd=aoe2mc.os.path.dirname(aoe2mc.__file__))
    dst = tmp_path / "base.scx"
    shutil.copy(src, dst)
    return src, dst


def test_de_scx_reads_as_aoe2scenario(de_scx):
    src, dst = de_scx
    a, b = aoe2mc.read_map(str(src)), aoe2mc.read_map(str(dst))
    assert a[0] == b[0] and (a[1] == b[1]).all() and len(a[5]) == len(b[5])   # same size, terrain, objects


def test_unknown_de_format_one_line(de_scx):
    _, dst = de_scx
    data = dst.read_bytes()
    dst.write_bytes(b"1.99" + data[4:12] + b"\xff" * 64)            # a format that no reader knows
    with pytest.raises(aoe2mc.ScxFormatError) as e:
        aoe2mc.read_map(str(dst))
    assert "1.99" in str(e.value) and "\n" not in str(e.value)
