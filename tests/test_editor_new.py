"""--new SIZE of the editor: a new empty map with no converted world first (#6077)."""
import json
import os
import sys

import pytest

sys.path[:0] = [os.path.join(os.path.dirname(__file__), "..", "game")]
import editor  # noqa: E402
import run  # noqa: E402


def test_new_world(tmp_path):
    world = editor.new_world(str(tmp_path / "W"), 40)
    data = json.load(open(os.path.join(world, "aoe2mc.json")))
    assert data["map_size"] == 40
    assert sum(bool(p.get("active")) for p in data["players"].values()) == 2


@pytest.mark.parametrize("args", [["--new", "tiny"], ["--editor", "o.aoe2scenario", "--new", "tiny"]])
def test_new_errors(tmp_path, args, monkeypatch):
    monkeypatch.setattr(editor, "new_world", lambda *a: pytest.fail("no world must be made"))
    with pytest.raises(SystemExit) as e:
        run.main([str(tmp_path), *args])
    assert e.value.code == 2
