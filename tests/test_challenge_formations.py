"""run.py --play --challenge battle-formations: both armies of the wiki page, the medal from the units lost (#3910)."""
import types

import pytest

from game import challenge

import army  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import cheats  # noqa: E402
import recap  # noqa: E402
import train  # noqa: E402

ROW = challenge.CHALLENGES["battle-formations"]


class Map:
    n, T = 64, 4

    def free(self, x, z):
        return 0 <= x < self.n and 0 <= z < self.n

    def y(self, x, z):
        return 64


def fake():
    g = types.SimpleNamespace(player=1, ended=None, challenge="battle-formations", sent=[], map=Map(), alive=set())
    g.command = g.sent.append
    g.positions = lambda uuids: {u: (0, 0, 0) for u in uuids if u in g.alive}
    return g


@pytest.fixture
def summons(monkeypatch):
    out = []

    def summon(g, name, pos, rotation=0, player=None):
        out.append((name, player, pos))
        g.alive.add(uuid := f"u{len(out)}")
        return uuid
    monkeypatch.setattr(train, "summon", summon)
    monkeypatch.setattr(recap, "game_time", lambda g: 100.0)
    return out


def test_the_challenge_places_both_armies_of_the_wiki_page(summons):
    g = fake()
    assert not army.battle(g, ROW)
    for player, units in ((1, ROW["army"]), (2, ROW["enemy"])):
        got = sorted(n for n, p, _ in summons if p == player)
        assert got == sorted(n for n, k in units.items() for _ in range(k))
    assert len({pos for *_, pos in summons}) == len(summons)           # one unit per cell


def test_all_enemy_units_dead_with_the_silver_limit_of_units_lost_end_the_game_with_the_silver_medal(summons, monkeypatch):
    won = []
    monkeypatch.setattr(cheats, "over", lambda g, w: won.append(w(1)) or setattr(g, "ended", "x"))
    monkeypatch.setattr(challenge, "keep", lambda *a: None)
    g = fake()
    challenge.tick(g)                                                  # places the armies
    assert won == [] and g.ended is None
    g.alive -= set(g.challenge_foes)
    g.losses = {f"l{i}": "PIKEMAN" for i in range(ROW["silver"])}
    challenge.tick(g)
    assert won == [True] and g.medal == "silver" and any("Silver medal" in c for c in g.sent)
