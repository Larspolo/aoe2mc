"""Attack gold with a part of a gold piece per minute (#4464, the Keshik: 21.75): the tag holds gold per 100 AoE2
minutes, and spoils.attacks takes the score and removes it. Test data, fake server of test_gather."""
import combat as plain
from test_attack_gold import score
from test_kill_spoils import game

from game import civs, combat, train


def test_a_part_rate_makes_exact_gold(monkeypatch):
    for m in (combat, plain):                                          # spoils imports the plain name
        monkeypatch.setattr(m, "ATTACK_GOLD", {"KNIGHT": 21.75})
    server, g = game("FRANKS")
    u = train.summon(g, "KNIGHT", (8.5, 64.0, 8.5))
    assert f"tag {u} add aoe2mc.gold.2175" in server.log             # no loss of the part
    n = {"n": 0}
    score(server, n)
    n["n"] = 4 * 40 * 2175                                             # 4 hits of 40 reload ticks
    train.census(g)
    want = 21.75 * 160 / 20 * combat.NORMAL / 60 * civs.value("attack_gold", "FRANKS", 1)
    assert abs(g.stock["gold"] + g.spare["gold"] - want) < 1e-9                    # the formula of spoils.attacks
    assert n["n"] == 0                                                 # the score goes back: no int overflow
    train.census(g)
    assert abs(g.stock["gold"] + g.spare["gold"] - want) < 1e-9       # the same hits give gold only once
