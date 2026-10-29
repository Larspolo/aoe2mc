"""The Art of War challenges open one after the other, and the medal file keeps the best medal of each (#3904)."""
import pytest

import challenge
import run


def after(name):
    """The first challenge that opens after a medal in challenge name."""
    return next(n for n, c in challenge.CHALLENGES.items() if c["after"] == name)


FIRST = next(n for n, c in challenge.CHALLENGES.items() if c["after"] is None and any(
    d["after"] == n and any(e["after"] == m for e in challenge.CHALLENGES.values())
    for m, d in challenge.CHALLENGES.items()))                         # an open one with two challenges after it
SECOND = after(FIRST)
THIRD = after(SECOND)


def test_a_medal_opens_the_next_challenge(tmp_path):
    f = str(tmp_path / "m.json")
    assert challenge.opened(FIRST, f) and not challenge.opened(SECOND, f)
    challenge.keep(FIRST, "bronze", f)
    assert challenge.opened(SECOND, f)


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
    challenge.keep(FIRST, "silver")
    with pytest.raises(SystemExit) as e:
        run.main(["WORLD", "--challenge", "list"])
    assert e.value.code == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == len(challenge.CHALLENGES)
    assert f"{FIRST}: open, silver medal" in lines and f"{SECOND}: open, no medal" in lines
    assert f"{THIRD}: closed, no medal" in lines


def test_a_closed_challenge_names_the_one_to_win_first(capsys):
    with pytest.raises(SystemExit):
        run.main(["WORLD", "--play", "--challenge", THIRD])
    assert f"win a medal in {SECOND} first" in capsys.readouterr().err
