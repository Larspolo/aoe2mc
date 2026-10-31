"""#4758: the AoE2 DE setting "Hidden civilizations" (run.py --hidden-civs): the lobby and Diplomacy menus show "?" for
the civilization of an enemy (decision #4754: A), an ally shows its civilization, and the recap book shows all."""
import json
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import diplomacy  # noqa: E402
import fog  # noqa: E402
import lobby  # noqa: E402
import recap  # noqa: E402
import savegame  # noqa: E402
from test_scenario_mode import game  # noqa: E402

CIVS = ("BRITONS", "CELTS", "FRANKS")


def hidden_game(on=True):
    players = {"0": {}, **{str(n): {"civ": c, "team": 1 if n < 3 else None} for n, c in enumerate(CIVS, 1)}}
    server, g, _ = game(players)
    g.data["hidden_civs"] = on
    g.game.people, g.game.sides = 3, {"steve": 1}
    return server, g


def test_diplomacy_hides_only_the_enemy():
    _, g = hidden_game()
    names = [it[2] for it in diplomacy.items(g) if it[0] < 9]
    assert names[0].endswith("(Celts)") and names[1].endswith("(?)")      # player 2: ally; player 3: enemy


def test_lobby_hides_only_the_enemy_of_the_viewer():
    _, g = hidden_game()
    names = [it[2] for it in lobby.items(g, "steve")]
    assert names == ["Player 1 (Britons)", "Player 2 (Celts)", "Player 3 (?)"]


def test_off_shows_all():
    _, g = hidden_game(False)
    assert [it[2] for it in lobby.items(g, "steve")][2] == "Player 3 (Franks)"
    assert lobby.name(g, 3, 1) == "Player 3 (Franks)" and lobby.name(SimpleNamespace(data={}, players={}), 3) == "Player 3"


def test_the_recap_book_shows_all_civilizations():
    _, g = hidden_game()
    g.data["objects"] = [{"player": n, "kind": "unit", "name": "VILLAGER"} for n in (1, 2, 3)]          # players of the map: each gets its recap line
    text = "".join(t for _, t in recap.parts(g, lambda n: n == 1))
    assert all(c.title() in text for c in CIVS) and "(?)" not in text


def test_an_enemy_civilization_shows_after_a_sight():
    """#4748: an enemy shows "?" until a unit of the player saw a unit of it (fog.meet); an ally shows from the start."""
    _, g = hidden_game()
    g.data["objects"].append({"kind": "unit", "name": "MILITIA", "player": 3, "uuid": "foe-1"})
    assert lobby.name(g, 3, 1) == "Player 3 (?)" and diplomacy.name(g, 3).endswith("(?)")
    assert lobby.name(g, 2, 1) == "Player 2 (Celts)"
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    fog.meet(g, state, {"foe-1"})
    assert lobby.name(g, 3, 1) == "Player 3 (Franks)" and diplomacy.name(g, 3).endswith("(Franks)")


def test_a_seen_building_shows_the_civilization():
    _, g = hidden_game()
    g.data["objects"].append({"kind": "building", "name": "CASTLE", "player": 3, "footprint": [8, 8, 10, 10]})
    state = vars(g).setdefault("fog", {"hidden": set(), "at": None})
    state["tiles"] = {(8 // g.map.T, 8 // g.map.T)}
    fog.remember(g, state)
    assert lobby.name(g, 3, 1) == "Player 3 (Franks)"


def test_a_save_keeps_the_seen_civilizations():
    _, g = hidden_game()
    vars(g).setdefault("fog", {"hidden": set(), "at": None})["civs"] = {3}
    d = json.loads(json.dumps(savegame.dump(g), sort_keys=True))
    assert d["players"]["1"]["civs_seen"] == [3]
    _, h = hidden_game()
    savegame.load(h, d)
    assert h.fog["civs"] == {3} and lobby.name(h, 3, 1) == "Player 3 (Franks)"
