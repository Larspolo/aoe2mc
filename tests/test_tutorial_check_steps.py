"""tools/tutorial_check.py (#5551): the driver has an input for each step of the tutorial and finds it by name."""
import tutorial_check

from game import tutorial


def test_the_driver_has_an_input_for_each_step():
    missing = [r["name"] for r in tutorial.STEPS if not callable(getattr(tutorial_check.Driver, f"do_{r['name']}", None))]
    assert not missing


def test_the_driver_finds_a_step_by_its_name():
    d = tutorial_check.Driver(None, None, "", 1)
    assert [d.at(r["name"]) for r in tutorial.STEPS] == list(range(len(tutorial.STEPS)))
