"""run.py --replay --takeover P: the first Minecraft player plays player P of the record (#5451)."""
import json
import types

import pytest
import run


def test_side_of_seat_player():
    sent = []
    game = types.SimpleNamespace(people=1, seats=(2,), sides={}, spectators=set(), placed=set(), kind="paper",
                                 command=sent.append, start_view=lambda name, n: None)
    run.Game.side(game, "steve")
    assert game.sides == {"steve": 2}
    assert "team join p2 steve" in sent
    run.Game.side(game, "alex")                      # a later one has no side
    assert "alex" not in game.sides and "team join spec alex" in sent


def test_takeover_unknown_player(tmp_path):
    (tmp_path / "level.dat").write_bytes(b"")
    (tmp_path / "aoe2mc.json").write_text(json.dumps({"players": {"0": {}, "1": {}, "2": {}}}))
    with pytest.raises(SystemExit) as e:
        run.main([str(tmp_path), "--replay", "--takeover", "9"])
    assert "--takeover 9" in str(e.value) and "\n" not in str(e.value)


def test_gather_of_player_1_reads_no_clicks_of_the_seat():
    game = types.SimpleNamespace(seats=(2,))
    assert run.click_who(game, 1, 1) == "@a[team=p1]"
    assert run.click_who(game, 1, 2) == "@a[team=p2]"
    assert run.click_who(types.SimpleNamespace(), 1, 1) == "@a"
