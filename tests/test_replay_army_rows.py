"""Live replay: the army rows show only military units in training and stay clear of the other sky texts (#3818)."""
import re

from test_replay_army_view import make, replay, shown

ROW = 0.3      # blocks of one text row of a text display at scale 1 (about 10 of 40 pixels per block, with a margin)


def test_a_villager_in_training_does_not_show_and_a_military_unit_does():
    r = make([{"time": 0, "player": 1, "kind": "queue", "type": 83, "objects": [5], "name": "VILLAGER_MALE"},
              {"time": 0, "player": 1, "kind": "queue", "type": 93, "objects": [5], "name": "SPEARMAN"}])
    line = shown(r.army_view(500)[0])["text"]
    assert "Villager" not in line and "training 1 Spearman" in line


def test_the_army_rows_do_not_overlap_the_other_sky_texts():
    r = make()
    r.upgrades = lambda p, t: [replay.SMITH[0][1][0]]               # one Blacksmith research: its display shows
    r.stats = lambda t: {p: [(0, 5, 3, 1, 100)] for p in (1, 2)}
    r.eco = lambda: {1: {"food": 3}, 2: {"wood": 2}}
    cmds = r.graphs(0) + r.upgrade_view(0) + r.ecoview() + r.army_view(0)
    spans = []
    for c in cmds:
        y = float(re.match(r"summon text_display \S+ (\S+) ", c)[1])
        spans.append((y, y + ROW * (c.count("\\n") + 1), c[-40:]))   # a display grows up from its place
    assert len(spans) == 4 + 1 + 1 + 2
    spans.sort()
    for (_, top, a), (bottom, _, b) in zip(spans, spans[1:]):
        assert top <= bottom, (a, b)
