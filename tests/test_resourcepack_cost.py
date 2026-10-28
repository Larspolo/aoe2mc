"""The cost of the resource pack (#2747): the launcher check box passes --resource-pack, and the help text of the
option and the box show the measured cost of the table in docs/resourcepack.md."""
import contextlib
import io
import re
from pathlib import Path

import pytest

import aoe2mc
import gui

ROOT = Path(__file__).resolve().parent.parent
O = {"input": "a.aoe2scenario", "output": "/saves/a"}


def test_the_launcher_passes_the_option_when_the_box_is_on():
    assert gui.argv(O | {"resource_pack": True})[2:] == ["--resource-pack"]
    assert "--resource-pack" not in gui.argv(O | {"resource_pack": False})


def test_the_box_and_the_help_show_the_cost_of_the_table():
    doc = (ROOT / "docs" / "resourcepack.md").read_text()
    size = re.search(r"\| `resources\.zip` size \|[^|]+\| (\d+\.\d) MB \|", doc).group(1)
    frame = re.search(r"\| Client frame time, median \|[^|]+\|[^|]+\| ([+-]\d+) % \|", doc).group(1)
    out = io.StringIO()
    with contextlib.redirect_stdout(out), pytest.raises(SystemExit):
        aoe2mc.main(["--help"])
    text = " ".join(out.getvalue().split())
    for shown in (gui.PACK_TEXT, text):
        assert f"{size} MB" in shown and f"{frame.lstrip('+')} % frame time" in shown
