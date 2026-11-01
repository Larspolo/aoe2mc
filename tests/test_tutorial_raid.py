"""The defense step of the tutorial (#5504): raid() summons the units of player 2 that attack the nearest own villager,
repelled() is True when all of them are dead."""
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "game"))
import tutorial  # noqa: E402

ROW = {s["name"]: s for s in tutorial.STEPS}


def fake(alive):
    g = types.SimpleNamespace(player=1, sent=[], villagers={
        "far": types.SimpleNamespace(uuid="far", pos=(60.0, 64.0, 60.0)),
        "near": types.SimpleNamespace(uuid="near", pos=(11.0, 64.0, 10.0))},
        map=types.SimpleNamespace(n=64, T=4, y=lambda x, z: 64))
    g.command = lambda c: g.sent.append(c) or ""
    g.positions = lambda uuids: {u: (0, 0, 0) for u in uuids if u in alive}
    return g


def test_raid_attacks_and_repelled(monkeypatch):
    import challenge
    import train
    summoned = []
    monkeypatch.setattr(challenge, "town", lambda g: (8, 12, 8, 12))
    monkeypatch.setattr(train, "summon", lambda g, n, pos, player=None: summoned.append((n, pos, player)) or
                        f"u{len(summoned)}")
    alive = set()
    g = fake(alive)
    tutorial.show(g, [s["name"] for s in tutorial.STEPS].index("raid"))
    want = sorted(n for n, k in ROW["raid"]["raid"].items() for _ in range(k))
    assert sorted(n for n, _, _ in summoned) == want and {p for _, _, p in summoned} == {2}
    assert summoned[0][1][0] == 30.5                                   # 20 blocks east of the town center
    assert {f"aoe attack {u} near" for u in g.tutorial_raid} <= set(g.sent)
    alive.update(g.tutorial_raid)
    assert not tutorial.done(g, ROW["raid"])
    alive.discard(g.tutorial_raid[0])
    assert not tutorial.done(g, ROW["raid"])
    alive.clear()
    assert tutorial.done(g, ROW["raid"])
