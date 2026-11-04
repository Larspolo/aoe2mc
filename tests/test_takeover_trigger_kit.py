"""The takeover trigger with a person online (#5701): the replay kit goes, the person gets the team and the town."""
import types

import replay
import replay_input
import run


def test_online_person_gets_the_game_after_the_trigger():
    sent = []
    game = types.SimpleNamespace(people=1, seats=(2,), sides={}, spectators=set(), placed=set(), kind="paper",
                                 joined={"steve"}, starts={2: (40, 70, 80)}, yaw=90.0, command=sent.append)
    game.start_view = lambda name, n: run.Game.start_view(game, name, n)
    run.drop_replay_kit(game)
    assert f"bossbar remove {replay.BAR}" in sent
    for n in replay_input.ITEMS:
        assert f"clear steve *[custom_data={{{replay_input.OBJECTIVE}:{n}}}]" in sent
    assert "gamemode creative steve" in sent
    for name in sorted({*game.sides, *vars(game).pop("taken", ())}):   # the loop of play()
        run.Game.side(game, name)
    assert game.sides == {"steve": 2} and "team join p2 steve" in sent
    assert "tp steve 40.5 70 80.5 90.0 0" in sent
    assert run.click_who(game, 1, 2) == "@a[team=p2]"     # the game items of the Gather of player 2 go to the team
