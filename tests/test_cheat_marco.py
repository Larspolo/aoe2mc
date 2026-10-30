"""The cheat code "marco" answers "polo": an easter egg with the name of the owner (#1057)."""
from test_cheats import game

from game import cheats


def test_marco_answers_polo(tiny_world):
    server, g = game(tiny_world, True)
    server.scores["aoe_cheat"] = cheats.NAMES.index("marco") + 1
    assert cheats.clicks(g) == [("Steve", "marco")]
    assert server.log[-1] == 'tellraw Steve {"text":"polo"}'
