"""The AI difficulty and the player type of an XS script (game/xs_host.py, #5876)."""
from types import SimpleNamespace as NS

from tests.test_xs_host import side, value
from tests.test_xs_players import players


def with_setting(setting):
    g = side()
    g.game = NS(settings={} if setting is None else {"ai_difficulty": setting})
    return g


def test_difficulty_is_the_aoe2_value_of_the_first_bot():
    assert value(with_setting("hard"), "xsGetDifficulty()") == 1
    assert value(with_setting("hard,easiest"), "xsGetDifficulty()") == 1
    assert value(with_setting(None), "xsGetDifficulty()") == 3          # no setting: standard


def test_difficulty_with_no_game_is_standard():
    assert value(side(), "xsGetDifficulty()") == 3


def test_player_type_gaia_computer_human_and_unknown():
    g = players(side())
    assert [value(g, f"xsGetPlayerType({n})") for n in (0, 1, 2, 9)] == [2, 1, 3, -1]
