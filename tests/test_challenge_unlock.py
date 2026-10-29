"""The Art of War challenges open one after the other, and the medal file keeps the best medal of each (#3904)."""
import pytest

import challenge
import run


def test_a_medal_opens_the_next_challenge(tmp_path):
    f = str(tmp_path / "m.json")
    assert challenge.opened("early-economy", f) and not challenge.opened("fast-castle-age", f)
    challenge.keep("early-economy", "bronze", f)
    assert challenge.opened("fast-castle-age", f)


def test_a_worse_medal_keeps_the_best_one(tmp_path):
    f = str(tmp_path / "m.json")
    challenge.keep("early-economy", "gold", f)
    challenge.keep("early-economy", "silver", f)
    challenge.keep("early-economy", None, f)
    assert challenge.medals(f) == {"early-economy": "gold"}
    challenge.keep("booming", "bronze", f)
    challenge.keep("booming", "silver", f)
    assert challenge.medals(f)["booming"] == "silver"


def test_list_prints_each_challenge_with_its_state(capsys):
    challenge.keep("early-economy", "silver")
    with pytest.raises(SystemExit) as e:
        run.main(["WORLD", "--challenge", "list"])
    assert e.value.code == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 9 == len(challenge.CHALLENGES)
    assert "early-economy: open, silver medal" in lines and "fast-castle-age: open, no medal" in lines
    assert "booming: closed, no medal" in lines


def test_a_closed_challenge_names_the_one_to_win_first(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--challenge", "booming"])
    assert "win a medal in fast-castle-age first" in capsys.readouterr().err
