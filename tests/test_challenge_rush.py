"""run.py --play --challenge rushing-the-enemy: 5 dead villagers of the enemy bot complete the goal (#3905, epic #3759)."""
import types

import pytest

from game import challenge

import build  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402


def fake(dead=5, seconds=290.0):
    """A Gather of player 1 in Rushing the Enemy with the bot of player 2: `dead` of its villagers and a soldier died."""
    enemy = types.SimpleNamespace(player=2, losses={**{f"v{i}": "VILLAGER" for i in range(dead)}, "s": "MILITIA"})
    g = types.SimpleNamespace(player=1, ended=None, challenge="rushing-the-enemy", sent=[], data={"objects": []},
                              bots=[types.SimpleNamespace(g=enemy)], seconds=seconds)
    g.command = g.sent.append
    return g


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


def test_the_fifth_dead_enemy_villager_at_290_seconds_gives_the_gold_medal(ends):
    g = fake()
    challenge.tick(g)
    assert ends == [True] and any("Gold medal" in c and "subtitle" in c for c in g.sent)


def test_4_dead_villagers_do_not_end_the_game(ends):
    g = fake(dead=4)
    challenge.tick(g)
    assert ends == [] and g.ended is None


def test_setup_places_the_enemy_buildings_and_villagers(monkeypatch):
    enemy = types.SimpleNamespace(player=2, villagers={"v0": None}, pop=1)
    g = types.SimpleNamespace(player=1, challenge="rushing-the-enemy", bots=[types.SimpleNamespace(g=enemy)])
    tc = (0, 16, 0, 16)
    placed = []
    monkeypatch.setattr(train, "homes", lambda h: {tc: "TOWN_CENTER"})
    monkeypatch.setattr(build, "near", lambda h, name, cell: (name, cell))
    monkeypatch.setattr(build, "found", lambda h, name, rect, free=False: {"name": name, "free": free})
    monkeypatch.setattr(build, "rise", lambda h, site, work: placed.append((site["name"], work)))
    monkeypatch.setattr(train, "spawn", lambda h, rect, name: h.villagers.setdefault(f"v{len(h.villagers)}", name))
    assert challenge.setup(g) is enemy
    assert sorted(n for n, _ in placed) == ["LUMBER_CAMP", "LUMBER_CAMP", "MILL", "MINING_CAMP"]
    assert len(enemy.villagers) == 15 and enemy.pop == 15


def test_a_challenge_without_an_enemy_has_no_setup():
    g = types.SimpleNamespace(player=1, challenge="booming", bots=[])
    assert challenge.setup(g) is None
