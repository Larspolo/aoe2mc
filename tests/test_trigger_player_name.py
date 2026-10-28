"""A trigger with the effect "Change Player Name" renames the team of its player in the converted world (#2711)."""
from collections import Counter

import aoe2mc
from test_trigger_objects import trig


def effect(message="The Enemy", player=2):
    return dict(type=aoe2mc.CHANGE_PLAYER_NAME, message=message, player=player, time=0, object=None, tile=[-1, -1],
                area=[-1] * 4)


def lines(e, stats=None):
    files = aoe2mc.trigger_files([trig([e])], stats=stats)[1]
    return files.get("data/aoe2mc/function/trigger/7.mcfunction", "").splitlines()


def test_the_team_of_the_player_gets_the_new_name():
    stats = Counter()
    assert lines(effect(), stats) == ['team modify p2 displayName {"text": "The Enemy"}']
    assert stats == Counter({"change player name": 1})


def test_the_name_has_no_color_tags():
    assert lines(effect("<RED>Señor Rojo")) == ['team modify p2 displayName {"text": "Señor Rojo"}']


def test_gaia_or_an_empty_name_gives_no_line():
    for e in (effect(player=0), effect(message=" <BLUE> ")):
        assert lines(e) == []
