"""The editor gives each placed object a stable reference ID (#6107): a remove of another object does not move it."""
import contextlib
import io
import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
import editor  # noqa: E402
from test_editor import FakeGame  # noqa: E402
from test_export_triggers import by_ref, read, world  # noqa: E402, F401


@pytest.fixture
def copy(world, tmp_path):  # noqa: F811
    path = str(tmp_path / "w")
    shutil.copytree(world[0], path)
    return path


def export(state, tmp_path, name):
    out = str(tmp_path / name)
    with contextlib.redirect_stdout(io.StringIO()):
        editor.save(state.game, out, state)
    return by_ref(read(out))


def source_refs(path):
    return [o["ref"] for o in json.load(open(os.path.join(path, "aoe2mc.json")))["objects"] if o.get("ref") is not None]


def test_a_remove_does_not_move_the_ref_of_a_later_object(copy, tmp_path):
    state = editor.State(FakeGame(copy))
    state.place(83, 2, (5.5, 6.5))
    state.place(4, 1, (7.5, 3.5))
    ref = state.placed[1]["ref"]
    assert by_ref_of(export(state, tmp_path, "a.aoe2scenario"), ref)[0] == 4
    state.placed.pop(0)                                              # as editor.remove
    state.place(83, 2, (9.5, 9.5))
    got = export(state, tmp_path, "b.aoe2scenario")
    assert got[ref][0] == 4 and state.placed[1]["ref"] != ref


def by_ref_of(refs, ref):
    return refs[ref]


def test_the_refs_are_unique_and_above_the_source(copy, tmp_path):
    state = editor.State(FakeGame(copy))
    for i in range(3):
        state.place(83, 1, (4.5 + i, 4.5))
    got = export(state, tmp_path, "c.aoe2scenario")
    placed = [o["ref"] for o in state.placed]
    assert len(set(placed)) == 3 and min(placed) > max(source_refs(copy))
    assert all(r in got for r in placed) and set(source_refs(copy)) <= set(got)


def test_an_old_save_with_no_ref_exports_as_before(copy, tmp_path):
    state = editor.State(FakeGame(copy))
    state.place(83, 2, (5.5, 6.5))
    del state.placed[0]["ref"]
    got = export(state, tmp_path, "d.aoe2scenario")
    assert max(got) == max(source_refs(copy)) + 1 and got[max(got)][0] == 83
