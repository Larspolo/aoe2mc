"""game/data/train.jsonl: no two train items of one building take the same menu slot for one civilization (#2236).
#2183 and #2157 both gave slot 23 of the barracks (Jian Swordsman, Temple Guard), and the jsonl merge gave no conflict:
a Muisca player saw both items in one slot, and train.order() took only one.

Two items may share a slot when one line of upgrades links them ("upgrade", "after": the new item replaces the old
one), or when no civilization has both (the regional units: Dromon, Lou Chuan and the cannon galleon). A player with no
civilization sees those regional items in one slot; a scenario player has a civilization."""
from collections import defaultdict

from game import civs, train


def linked():
    """{name: the names of its line of upgrades}: the groups of the "after" and "upgrade" links."""
    link = defaultdict(set)
    pairs = list(train.AFTER.items()) + [(t, n) for t in train.UPGRADES for p in train.lines(t) for n in p] \
        + [p for t in train.UPGRADES for p in train.lines(t)]
    for a, b in pairs:
        link[a].add(b)
        link[b].add(a)
    out = {}
    for n in list(link):
        group, todo = {n}, [n]
        while todo:
            new = link[todo.pop()] - group
            group |= new
            todo += new
        out[n] = group
    return out


def clashes(rows=train.ROWS):
    """(building, slot, item, item, a civilization that sees both) of each clash."""
    groups, slots, everyone = linked(), defaultdict(list), sorted(r["name"] for r in civs.ROWS)
    for r in rows:
        if r.get("building"):                                       # the castle items of a civ: train.trains()
            slots[r["building"], r["slot"]].append(r["name"])
    out = []
    for (b, s), names in slots.items():
        for i, a in enumerate(names):
            for c in names[i + 1:]:
                both = [v for v in everyone if v not in civs.MISSING.get(a, ()) + civs.MISSING.get(c, ())]
                if c not in groups.get(a, ()) and both:
                    out.append((b, s, *sorted((a, c)), both[0]))
    return out


def test_no_civilization_sees_two_items_in_one_slot():
    assert clashes() == []


def test_a_clash_fails():
    slot = next(r["slot"] for r in train.ROWS if r["name"] == "TEMPLE_GUARD")      # as the Jian Swordsman of #2183
    rows = [r | {"slot": slot} if r["name"] == "SPEARMAN" else r for r in train.ROWS]
    assert ("BARRACKS", slot, "SPEARMAN", "TEMPLE_GUARD", "MUISCA") in clashes(rows)

