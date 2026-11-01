"""tools/tutorial_check.py (#5551): the driver has an input for each step of the tutorial, found by its name."""
import tutorial_check

from game import tutorial


def driver():
    return tutorial_check.Driver(type("G", (), {"ended": None})(), None, "", 1)


def test_each_step_of_the_tutorial_has_an_input():
    names = [r["name"] for r in tutorial.STEPS]
    assert set(names) <= set(driver().inputs())


def test_the_driver_finds_a_step_by_its_name():
    d = driver()
    assert [d.at(r["name"]) for r in tutorial.STEPS] == list(range(len(tutorial.STEPS)))
