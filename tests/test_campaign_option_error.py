import contextlib
import io

import pytest

import aoe2mc
from test_campaign import cpx, scx_bytes


def test_wrong_option_for_a_readable_old_scenario_is_a_usage_error(tmp_path):
    """A player that the scenario does not have stops the run with a usage error, not with the DE editor steps (#3036)."""
    a = scx_bytes(tmp_path, "a.scx", {1: (1, 0, (8, 8))})
    c = cpx(tmp_path / "old.cpx", [("Gut.scx", a)])
    err = io.StringIO()
    with pytest.raises(SystemExit) as e, contextlib.redirect_stderr(err):
        aoe2mc.main([str(c), str(tmp_path / "out"), "--player-architecture", "5=western"])
    assert e.value.code == 2
    assert "--player-architecture" in err.getvalue()
    assert not (tmp_path / "out" / "1 Gut.scx").exists()
