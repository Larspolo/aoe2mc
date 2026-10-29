"""Live replay: a monk that dies drops its relic at its place, and a monastery that falls drops its relics at its door
(#4013). Fake RCON."""
from test_replay_relic_monastery import CHURCH, home
from test_replay_relic_pickup import MONK, MONK2, RELIC, order, pickups, play

RELIC2 = dict(RELIC, ref=31, tile=[5.5, 12.5])


def delete(t, i, name):
    return dict(time=t, player=1, kind="delete", objects=[i], names=[name])


def pots(sent):
    return [c for c in sent if c.startswith("setblock ") and c.endswith("decorated_pot keep")]


def test_a_dead_monk_drops_its_relic_and_another_monk_picks_it_up():
    r, sent = play([order(0, 7, "MONK"), delete(15000, 7, "MONK"), order(16000, 8, "MONK")], [MONK, MONK2, RELIC],
                   end=45000)
    assert r.relics[30]["monk"] == 8 and len(pots(sent)) == 1
    x, z = (int(c) for c in pots(sent)[0].split()[1:4:2])
    assert abs(x - 22) <= r.T and abs(z - 42) <= r.T                # near the place where the monk took it
    assert len(pickups(sent, "m2")) == 1


def test_a_fallen_monastery_drops_its_relics_at_its_door():
    r, sent = play([order(0, 7, "MONK"), home(15000, 40), dict(order(46000, 8, "MONK"), target=31),
                    dict(home(61000, 40), objects=[8]), delete(91000, 40, "MONASTERY")],
                   [MONK, MONK2, RELIC, RELIC2, CHURCH], end=95000)
    assert r.relic_count(1) == 0 and all(q["home"] is None and q["at"] for q in r.relics.values())
    cells = {q["at"] for q in r.relics.values()}
    assert len(cells) == 2 and all(c in r.map.front((30, 42, 40, 52)) for c in cells)


def test_a_monk_that_the_census_finds_dead_drops_its_relic():
    r, sent = play([order(0, 7, "MONK")], [MONK, RELIC])
    v = r.units[7]
    r.census(30000)
    r.flush()
    assert r.relics[30]["monk"] is None and r.relics[30]["at"] == (int(v.pos[0]), int(v.pos[2]))
    assert r.game.sent[-1].endswith("decorated_pot keep")
