"""The stance menu of a unit is valid on Paper (#3661): 26.3 has no item "chain", so the menu did not open."""
import shutil
import types

import pytest

from game import stance


@pytest.mark.mc
def test_the_stance_menu_is_valid_on_paper(tiny_world, tmp_path):
    from test_paper import paper_reachable
    if not paper_reachable():
        pytest.skip("Paper is not reachable")
    from game import menu, run
    world = shutil.copytree(tiny_world[0], tmp_path / "W")
    with run.Game(world) as game:
        items = stance.items(types.SimpleNamespace(), "u")
        answers = [game.command(c).strip() for c in menu.commands("@a", "Stance", items)]
        assert answers == ["Menu: 0 players"] * len(answers)          # no "Bad item"
