"""Live replay: a monk brings a relic into a monastery that the replay built (no object ID in the record, #4602).
Fake RCON."""
from test_replay_relic_pickup import MONK, RELIC, order, play

MONASTERY = 104              # the AoE2 object ID of the monastery


def test_a_monk_puts_the_relic_into_a_built_monastery():
    build = dict(time=0, player=1, kind="build", type=MONASTERY, name="MONASTERY", tile=[9.0, 11.5], objects=[])
    home = dict(time=15000, player=1, kind="order", objects=[7], target=999, target_name="MONASTERY", tile=[9.0, 11.5],
                names=["MONK"])
    r, sent = play([build, order(1000, 7, "MONK"), home], [MONK, RELIC], end=60000)
    assert r.placed and r.relics[30]["monk"] is None and r.relic_count(1) == 1
    assert r.relics[30]["home"] == r.placed[0][2]
