"""The AI names of the co-op scenario Honfoglalas (#5834): the .per2 files of a scenario, the airef ids of positions,
civilizations and units, and my-player-number as a number."""
from test_bot_gather import bot_map

from game import per
from game.bot import build, train  # noqa: F401  the modules that per uses


def run(body):
    server, me, b = bot_map()
    me.bots = [b]
    s = per.Script(per.parse(f"(defrule (true) => {body})"), b)
    s.step()
    return s


def test_load_finds_per2_file():
    files = {"Scenario Upgrades DE.per2": "(defrule (true) => (do-nothing))"}
    assert per.find_in(files, "scenario upgrades DE") == "Scenario Upgrades DE.per2"
    assert per.find_in({**files, "scenario upgrades DE.per": ""}, "scenario upgrades DE") == "scenario upgrades DE.per"
    assert per.find_in(files, "scenario upgrades DE.per") is None          # a given extension stays
    assert len(per.parse('(load "scenario upgrades DE")', files=files)) == 1


def test_position_by_airef_id(capsys):
    for i, name in per.POSITION_IDS.items():
        s = run(f"(up-get-point {i} 100)")
        assert (s.goals[100], s.goals[101]) == (lambda t: (t.goals[100], t.goals[101]))(run(f"(up-get-point {name} 100)"))
    assert "unknown position" not in capsys.readouterr().err


def test_unit_and_civ_by_airef_id(capsys):
    server, me, b = bot_map()
    s = per.Script([], b)
    for i, name in list(per.OBJECT_IDS.items()):
        row = per.names()[name]
        if "game" in row:
            assert s.game(i, row["kind"]) == row["game"]
    for i, name in per.CIV_IDS.items():
        assert s.game(i, "civ") == per.names()[name]["game"]
    assert "unknown" not in capsys.readouterr().err


def test_my_player_number_is_a_number(capsys):
    s = run("(set-goal 7 my-player-number)")
    assert s.goals[7] == s.bot.g.player
    assert "unknown number" not in capsys.readouterr().err
