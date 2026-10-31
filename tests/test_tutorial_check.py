"""tools/tutorial_check.py: the level-4 check of the tutorial (#5228). No server here: the form of the tool."""
import pytest
import tutorial_check

from game import tutorial


def test_a_folder_without_level_dat_stops(tmp_path):
    with pytest.raises(SystemExit, match="no level.dat"):
        tutorial_check.main([str(tmp_path), str(tmp_path / "out")])


def test_the_driver_counts_the_steps_of_the_tutorial():
    g = type("G", (), {"ended": None})()
    g.tutorial_step = len(tutorial.STEPS)
    d = tutorial_check.Driver(g, None, "", 1)
    assert d.step() == len(tutorial.STEPS) and d.wait(0, 0)
