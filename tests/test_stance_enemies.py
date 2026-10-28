"""After a change of the stances, `enemies` of each side follows the new alliances (#2996): owners.update_enemies runs
after scenario.diplomacy, diplomacy.change, conquest.last_man and savegame.load."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import conquest  # noqa: E402
import diplomacy  # noqa: E402
import gather  # noqa: E402
import owners  # noqa: E402
import savegame  # noqa: E402
import scenario  # noqa: E402


def game(players, scores=None):
    """Player 1 with the bots 2 and 3, one unit m-N of each player, the trained unit t-2 of player 2."""
    log, scores = [], dict(scores or {})

    def command(cmd):
        log.append(cmd)
        w = cmd.split()
        if w[:3] == ["scoreboard", "players", "get"]:
            return f"{w[3]} has {scores[w[3]]} [aoe_dip]" if w[3] in scores else "none is set"
        if w[:3] == ["scoreboard", "players", "reset"]:
            scores.pop(w[3], None)
        return ""
    data = {"objects": [{"kind": "unit", "name": "MILITIA", "player": n, "uuid": f"m-{n}"} for n in (1, 2, 3)],
            owners.KEY: {"t-2": 2}}

    def side(n):
        return types.SimpleNamespace(player=n, players=players, data=data, command=command, paper=False, peers=[],
                                     bots=[], soldiers={}, game=types.SimpleNamespace(treaty=0.0, treaty_time=0.0),
                                     enemies={o["uuid"]: o["name"] for o in data["objects"]
                                              if not gather.allied(players, n, o["player"])})
    g = side(1)
    g.enemies |= {"t-2": "MILITIA"} if not gather.allied(players, 1, 2) else {}
    g.bots, g.scores = [types.SimpleNamespace(g=side(n)) for n in (2, 3)], scores
    return g


def test_a_trigger_makes_an_ally_an_enemy_and_an_enemy_an_ally():
    g = game({"0": {}, "1": {"team": 1}, "2": {}, "3": {"team": 1}}, {"#any": 1, "#p1.p3": 4})
    scenario.diplomacy(g)
    g.scores.update({"#any": 1, "#p1.p2": 1})                          # a second trigger
    scenario.diplomacy(g)
    assert not gather.allied(g.players, 1, 3) and gather.allied(g.players, 1, 2)
    assert sorted(g.enemies) == ["m-3"]
    assert sorted(g.bots[1].g.enemies) == ["m-1", "m-2", "t-2"]


def test_a_click_on_the_diplomacy_page_makes_an_enemy_an_ally(monkeypatch):
    g = game({"0": {}, "1": {}, "2": {}, "3": {}})
    monkeypatch.setattr(diplomacy, "show", lambda g, player: None)     # no menu here
    while not gather.allied(g.players, 1, 2):
        diplomacy.change(g, "Steve", 2)
    assert sorted(g.enemies) == ["m-3"]


def test_last_man_standing_makes_the_last_allies_enemies():
    g = game({"0": {}, "1": {"team": 1}, "2": {"team": 1}, "3": {"team": 2}})
    assert sorted(g.enemies) == ["m-3"]
    conquest.last_man(g, [1, 2], [3], gather.allied, gather.allies_command)
    assert sorted(g.enemies) == ["m-2", "m-3", "t-2"]


def test_a_load_follows_the_saved_stances():
    g = game({"0": {}, "1": {}, "2": {}, "3": {}})
    savegame.load(g, {"players": {}, "stances": {"1": {"team": 1}, "3": {"team": 1}}})
    assert sorted(g.enemies) == ["m-2", "t-2"]


def test_a_trained_unit_stays_an_enemy_and_a_killed_unit_stays_out():
    g = game({"0": {}, "1": {}, "2": {}, "3": {}}, {"#any": 1, "#p1.p3": 1})
    owners.killed(g, {"m-2"})
    scenario.diplomacy(g)
    assert sorted(g.enemies) == ["t-2"]
