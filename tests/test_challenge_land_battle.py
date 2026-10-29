"""run.py --play --challenge land-battle: six enemy waves, one after the other, and the medal from the units lost (#3906)."""
import types

import pytest

from game import challenge

import ai  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402

ROW = challenge.CHALLENGES["land-battle"]


class Map:
    n, T = 64, 4

    def free(self, x, z):
        return 0 <= x < self.n and 0 <= z < self.n

    def y(self, x, z):
        return 64


@pytest.fixture
def game(monkeypatch):
    g = types.SimpleNamespace(player=1, ended=None, challenge="land-battle", sent=[], map=Map(), alive=set(),
                              summons=[], attacks=[], won=[])
    g.command = g.sent.append
    g.positions = lambda uuids: {u: (0, 0, 0) for u in uuids if u in g.alive}

    def summon(g, name, pos, rotation=0, player=None):
        g.summons.append((name, player))
        g.alive.add(uuid := f"u{len(g.summons)}")
        return uuid
    monkeypatch.setattr(train, "summon", summon)
    monkeypatch.setattr(ai, "attack", lambda g, uuids, names, T, target: g.attacks.append((tuple(uuids), target)))
    monkeypatch.setattr(recap, "game_time", lambda g: 100.0)
    monkeypatch.setattr(cheats, "over", lambda g, w: g.won.append(w(1)) or setattr(g, "ended", "x"))
    monkeypatch.setattr(challenge, "keep", lambda *a: None)
    return g


def enemies(g):
    return sorted(n for n, p in g.summons if p == 2)


def test_the_next_wave_comes_only_when_the_wave_before_it_is_dead_and_3_losses_give_silver(game):
    g, waves = game, ROW["waves"]
    assert len(waves) == 6
    challenge.tick(g)
    assert enemies(g) == sorted(n for n, k in waves[0].items() for _ in range(k)) and len(g.attacks) == 1
    challenge.tick(g)
    assert len(g.attacks) == 1                                         # wave 1 lives: no wave 2
    for i in range(1, 6):
        g.alive -= set(g.challenge_foes)
        challenge.tick(g)
        assert g.challenge_wave == i and g.attacks[-1][0] == tuple(g.challenge_foes) and g.won == []
    g.losses = {"a": "ARCHER", "b": "SPEARMAN", "c": "SKIRMISHER"}
    g.alive -= set(g.challenge_foes)
    challenge.tick(g)
    assert g.won == [True] and g.medal == "silver" and any("Silver medal" in c for c in g.sent)


def test_the_boss_bar_of_a_lost_challenge_shows_the_units_lost_and_the_next_limit(game):
    g = game
    challenge.tick(g)
    g.losses = {"a": "ARCHER", "b": "SPEARMAN"}
    challenge.tick(g)
    assert any("bossbar set" in c and "2 units lost, gold medal up to 0" not in c and "2 units lost, silver medal up to 5"
               in c for c in g.sent)
    assert any(c == "bossbar set aoe2mc:challenge value 2" for c in g.sent)
