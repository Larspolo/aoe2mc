"""game/per.py: the facts starting-resources and fe-sub-game-type read the setup of the game (#5129). The map of
test_bot_gather: the bot is player 2."""
import pytest
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  (the modules that per uses)


def goal(text, setup):
    """Run one rule that sets goal 1 when its facts are true, on a bot whose Gather gets the attributes of setup."""
    server, me, b = bot_map()
    vars(b.g).update(setup)
    s = per.Script(per.parse(f"(defrule {text} => (set-goal 1 1))"), b)
    s.step()
    return s.goals.get(1) == 1


@pytest.mark.parametrize("setting, name", sorted(
    (k, n) for k, v in per.STARTING_RESOURCES.items() for n, w in per.RESOURCE_NAMES.items() if v == w))
def test_starting_resources(setting, name):
    assert goal(f"(starting-resources == {name})", {"resources": setting})
    other = next(n for n, w in per.RESOURCE_NAMES.items() if w != per.RESOURCE_NAMES[name])
    assert not goal(f"(starting-resources == {other})", {"resources": setting})


def test_default_is_low():
    assert goal("(starting-resources == low-resources)", {})
    assert goal("(starting-resources < medium-resources)", {})


@pytest.mark.parametrize("name", sorted(per.SUB_GAME_TYPES))
def test_sub_game_on(name):
    mode = name.removeprefix("sub-game-type-")
    setup = {"victory": mode} if mode == "king-of-the-hill" else {"modes": frozenset({mode})}
    assert goal(f"(fe-sub-game-type == {name})", setup)
    assert not goal(f"(fe-sub-game-type == {name})", {})


def test_several_modes_and_main_mode():
    setup = {"mode": "capture-the-relic", "modes": frozenset({"capture-the-relic", "regicide", "sudden-death"})}
    assert goal("(fe-sub-game-type == sub-game-type-regicide)", setup)
    assert goal("(fe-sub-game-type == sub-game-type-sudden-death)", setup)
    assert not goal("(fe-sub-game-type == sub-game-type-empire-wars)", setup)
    main = {"mode": "regicide", "modes": frozenset({"regicide"})}           # a game mode, not a lobby mode
    assert not goal("(fe-sub-game-type == sub-game-type-regicide)", main)
    assert goal("(fe-sub-game-type == 0)", main)
