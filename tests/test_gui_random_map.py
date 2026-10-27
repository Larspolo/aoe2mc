"""gui.py: a world from a random map of the own generators, with no input file (#1871)."""
import argparse

import pytest

import aoe2mc
import gui


def parser():
    """The argument parser of aoe2mc.main()."""
    found = []

    def stop(self, args=None, namespace=None):
        found.append(self)
        raise SystemExit(0)

    mp = pytest.MonkeyPatch()
    mp.setattr(argparse.ArgumentParser, "parse_args", stop)
    try:
        with pytest.raises(SystemExit):
            aoe2mc.main([])
    finally:
        mp.undo()
    return found[0]


def test_random_maps_are_the_choices_of_the_converter():
    choices = next(a.choices for a in parser()._actions if "--random-map" in a.option_strings)
    assert gui.RANDOM_MAPS == tuple(choices)


def test_argv_of_a_random_map_has_no_input_file(monkeypatch):
    a = gui.argv({"input": "", "output": "OUT", "random_map": "arabia", "seed": "7"})
    assert a[0] == "OUT" and "" not in a
    assert a[a.index("--seed") + 1] == "7" and a[a.index("--random-map") + 1] == "arabia"
    got = []
    monkeypatch.setattr(aoe2mc, "convert", lambda scenario, output, **kw: got.append((scenario, output, kw)))
    aoe2mc.main(a)
    assert got[0][:2] == (aoe2mc.RANDOM_MAP + "arabia", "OUT") and got[0][2]["seed"] == 7


def test_argv_without_a_random_map_keeps_the_input_file():
    a = gui.argv({"input": "IN.aoe2record", "output": "OUT", "random_map": "", "at": "5:00"})
    assert a[:2] == ["IN.aoe2record", "OUT"] and "--random-map" not in a and a[-2:] == ["--at", "5:00"]
