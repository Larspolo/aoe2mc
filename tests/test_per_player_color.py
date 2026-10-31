"""up-get-player-color with a player term (airef, #5094): a number, target-player or my-player-number store the ColorId
(1 to 8); an unknown term warns once and leaves the goal."""
from test_per_bot import scripted


def test_player_terms_store_a_color_id_from_1_to_8():
    s = scripted("(defrule (true) => (disable-self))").script
    for term in ("my-player-number", 2, "target-player"):
        s.goals.pop(50, None)
        s.act(0, ("up-get-player-color", term, 50))
        assert 1 <= s.goals[50] <= 8, term


def test_unknown_player_term_warns_and_keeps_the_goal(capsys):
    s = scripted("(defrule (true) => (disable-self))").script
    s.goals[50] = 7
    s.act(0, ("up-get-player-color", "lobby-player-9", 50))
    s.act(0, ("up-get-player-color", "lobby-player-9", 50))
    assert s.goals[50] == 7
    assert capsys.readouterr().err.count("unknown player lobby-player-9") == 1
