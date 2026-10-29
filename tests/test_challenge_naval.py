"""run.py --play --challenge naval-battle: both fleets on water, the medal by the ships lost (#3909, epic #3759)."""
import types

import pytest

from game import challenge

import cheats  # noqa: E402  (game/ is on sys.path after the import of game.challenge)
import recap  # noqa: E402
import train  # noqa: E402


class Map:
    """16 x 16 blocks: land in the columns x < 2, the rest is water."""
    n = 16

    def wet(self, x, z):
        return 2 <= x < self.n and 0 <= z < self.n

    def sea(self, x, z):
        return 62.0


def fake(lost=4, alive=()):
    g = types.SimpleNamespace(player=1, ended=None, challenge="naval-battle", sent=[], map=Map(), seconds=900.0,
                              losses={f"u{i}": "FIRE_SHIP" for i in range(lost)}, challenge_enemy=["e1", "e2"])
    g.command = g.sent.append
    g.positions = lambda uuids: {u: (0, 0, 0) for u in uuids if u in alive}
    return g


@pytest.fixture
def ends(monkeypatch):
    out = []
    monkeypatch.setattr(recap, "game_time", lambda g: g.seconds)
    monkeypatch.setattr(cheats, "over", lambda g, won: out.append(won(1)) or setattr(g, "ended", "x"))
    return out


def test_both_fleets_are_on_water_and_apart(monkeypatch):
    placed = []
    monkeypatch.setattr(train, "summon", lambda g, name, pos, player=None: placed.append((name, pos, player))
                        or f"s{len(placed)}")
    g = fake()
    challenge.setup(g)
    row = challenge.CHALLENGES["naval-battle"]
    assert sum(row["fleet"].values()) + sum(row["enemy_fleet"].values()) > len(placed) == 16   # 16 open water cells
    assert all(g.map.wet(int(x), int(z)) for _, (x, _, z), _ in placed)
    own = [p for p in placed if p[2] == 1]
    enemy = [p for p in placed if p[2] == 2]
    assert own and enemy and len(g.challenge_enemy) == len(enemy)
    assert max(x for _, (x, _, _), _ in own) <= min(x for _, (x, _, _), _ in enemy)
    assert len({(x, z) for _, (x, _, z), _ in placed}) == len(placed)


def test_all_enemy_warships_dead_with_4_ships_lost_give_the_gold_medal(ends):
    g = fake(lost=4)
    challenge.tick(g)
    assert ends == [True] and any("Gold medal" in c and "subtitle" in c for c in g.sent)


def test_5_ships_lost_give_the_silver_medal(ends):
    g = fake(lost=5)
    challenge.tick(g)
    assert any("Silver medal" in c and "subtitle" in c for c in g.sent)


def test_a_live_enemy_warship_does_not_end_the_game(ends):
    g = fake(alive={"e2"})
    challenge.tick(g)
    assert ends == [] and any("4 units lost, gold medal up to 4" in c for c in g.sent)
