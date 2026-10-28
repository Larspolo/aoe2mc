"""The stances and the sight that the triggers set (#2989) stay in a save, also without the "Lock Teams" option. A
--teams value given with --load wins over the saved stances (#2325)."""
import types

from test_bot_attack import armed

from game import savegame, scenario


def test_a_trigger_stance_and_sight_stay_after_a_save_and_a_load():
    _, me, _ = armed()
    me.players = {"1": {"team": 1}, "2": {"team": 1}, "3": {}}
    scenario.stance(me.players, 1, 3, "ally")                          # a trigger: player 1 allies player 3
    me.players["1"]["sees"] = [2]                                      # a trigger: "Set Player Visibility"
    state = savegame.dump(me)
    assert "stances" in state and not me.data.get("unlock_teams")
    _, new, _ = armed()
    new.players = {"1": {"team": None}, "2": {"team": None}, "3": {"team": None}}
    sent = []
    new.command = lambda c: sent.append(c) or ""
    savegame.load(new, state)
    assert new.players["1"]["sees"] == [2] and "sees" not in new.players["2"]
    assert new.players["3"]["team"] == me.players["1"]["team"] is not None   # the alliance of the trigger is back
    assert any(c.startswith("aoe allies ") for c in sent)


def test_a_given_teams_option_drops_the_saved_stances():
    state = {"players": {}, "stances": {"1": {"team": 2}}}
    savegame.settings(types.SimpleNamespace(), state, {"teams"})
    assert "stances" not in state
