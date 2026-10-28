"""
Record Game (#2649), the AoE2 lobby setting: `game/run.py --play --record FILE` writes the orders of the game as the
"timeline" of aoe2mc.json (aoe2mc.read_timeline: "time" in ms of game time, "player", "kind" and the keys of
aoe2mc.TIMELINE_KEYS), and `game/run.py --replay --replay-file FILE` plays them again on the same world (replay.Replay).
The file has one JSON line per event, so a stopped game keeps its events. Its first line holds the IDs of the start
objects ({"refs": {key: ID}}): the game program knows a unit by its UUID and a building by its footprint, a record by
its object ID. A start object keeps its "ref" of aoe2mc.json; a new object (a foundation, a trained unit) takes the next
ID when it appears, as in the model of aoe2mc.name_timeline. Recorded: a building (each wall piece as one), a unit in a queue,
a research, an age, a move and an attack order of the human player (the bots: their buildings, queues and ages).
The setups of run.play (the scout of a civilization, the start buildings, the town and units of a game mode) come at
0:00, before the game starts (#3028): a free foundation is a "build" event with "free", a unit that a setup kills a
"delete" event with "free" (no loss), and a unit that it summons a "summon" event with its new ID and tile.
"""
import functools
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import aoe2mc  # noqa: E402


class Recorder:
    def __init__(self, path, objects):
        self.f, self.time, self.ids, self.clock = open(path, "w"), 0.0, {}, None   # game seconds; UUID or footprint -> ID
        self.setup = True                                              # until play(): the setups of run.play (#3028)
        self.rects = {}                                                # UUID of a building -> its footprint (x0, x1, z0, z1)
        for o in objects:
            if o["kind"] == "building" and "footprint" in o:
                x0, z0, x1, z1 = o["footprint"]
                self.remember((x0, x1, z0, z1))
        keys = [(start_key(o), o.get("ref")) for o in objects]
        self.ids = {k: ref for k, ref in keys if k and ref is not None}
        self.top = max((o.get("ref") or 0 for o in objects), default=0)   # above the trees and mines too (#3001)
        for k, ref in keys:                                            # a start object with no ref takes the next ID,
            if k and ref is None:                                      # so it is older than the new objects
                self.top += 1                                          # (aoe2mc.name_timeline)
                self.ids[k] = self.top
        self.write({"refs": self.ids})

    def write(self, line):
        self.f.write(json.dumps(line) + "\n")
        self.f.flush()

    def remember(self, rect):
        """Keep the UUID of the building of footprint rect (x0, x1, z0, z1): an attack names the building by it (#3004)."""
        import combat                                                  # combat imports gather, which imports this module
        self.rects[combat.target_uuid([rect[0], rect[2], rect[1], rect[3]])] = tuple(int(v) for v in rect)

    def id(self, thing):
        """The object ID of a UUID or a building footprint (x0, x1, z0, z1): a new one gets the next ID. The UUID of a
        building (an attack, Gather.attack) is the ID of its footprint."""
        if isinstance(thing, str):
            thing = self.rects.get(thing, thing)
        else:
            self.remember(thing)
        k = thing if isinstance(thing, str) else key(thing)
        if k not in self.ids:
            self.top += 1
            self.ids[k] = self.top
            self.write({"refs": {k: self.top}})
        return self.ids[k]


def key(rect):
    return ",".join(str(int(v)) for v in rect)


def start_key(o):
    """The key of a start object of aoe2mc.json: the footprint of a building, the UUID of a unit, or None."""
    if o["kind"] == "building" and "footprint" in o:
        x0, z0, x1, z1 = o["footprint"]
        return key((x0, x1, z0, z1))
    return o.get("uuid") if o["kind"] == "unit" else None


@functools.lru_cache(maxsize=None)
def types():
    """Name -> AoE2 object ID of the buildings and units (the first ID of a name)."""
    out = {}
    for i, (prefix, name) in sorted(aoe2mc.object_kinds(old=False).items()):
        if prefix in ("B", "U", "H"):
            out.setdefault(name, i)
    return out


def start(gathers, path):
    """Record the game of the Gathers (the human player and the bots) into path."""
    r = Recorder(path, gathers[0].data.get("objects", ()))
    r.clock = gathers[0]                                               # its Gather.run counts the game time
    for g in gathers:
        g.record = r


def play(gathers):
    """The setups of run.play end and the game starts: a summoned unit is no longer a setup (a trained unit takes its
    ID in trained())."""
    for g in gathers:
        if (r := getattr(g, "record", None)) is not None:
            r.setup = False


def tick(g, dt):
    """Count dt game seconds (Gather.run of the human player)."""
    if (r := getattr(g, "record", None)) is not None and r.clock is g:
        r.time += dt


def event(g, kind, **data):
    """Write one timeline event of the player of g."""
    if (r := getattr(g, "record", None)) is None:
        return None
    e = {"time": int(round(r.time * 1000)), "player": g.player, "kind": kind} | data
    r.write(e)
    return e


def tile(g, rect):
    """The AoE2 tile [x, y] of the middle of the block footprint (x0, x1, z0, z1)."""
    x0, x1, z0, z1 = rect
    return [round((x0 + x1) / 2 / g.map.T, 3), round((z0 + z1) / 2 / g.map.T, 3)]


def built(g, name, rect, free=False):
    """A foundation of name on the footprint rect (build.place). free: a free one of a setup or a trigger, which the
    replay does not pay for (#3028)."""
    if getattr(g, "record", None) is not None and name in types():
        g.record.id(rect)
        event(g, "build", type=types()[name], name=name, tile=tile(g, rect), **{"free": True} if free else {})


def summoned(g, uuid, name, pos, player=None):
    """A unit that a setup summons at the block position pos (train.summon: the scout of scout.swap, the villagers
    of Empire Wars, the King of Regicide, #3028): a "summon" event with its new ID, which the replay summons at its
    tile. A unit of the game (a queue: trained(), a cheat) writes none."""
    import train                                                       # train imports this module
    if (r := getattr(g, "record", None)) is None or not r.setup or (unit := train.value("aoe2_name", name, name)) \
            not in types() or not isinstance(uuid, str):
        return
    i = r.id(uuid)
    event(g, "summon", type=types()[unit], name=name, objects=[i], tile=[round(pos[0] / g.map.T, 3),
          round(pos[2] / g.map.T, 3)], free=True, **{"player": player} if player not in (None, g.player) else {})


def removed(g, uuid):
    """A unit that a setup kills (cheats.transform of scout.swap, #3028): a "delete" event of its ID, no loss."""
    if (r := getattr(g, "record", None)) is not None and r.setup:
        event(g, "delete", objects=[r.id(uuid)], free=True)


def queued(g, name, rect):
    """A unit, a research or an age in the queue of the building rect (train.queue)."""
    if getattr(g, "record", None) is None:
        return
    import train                                                       # train imports this module
    at = [g.record.id(rect)]
    unit = train.value("aoe2_name", name, name)                        # a unit with another AoE2 name (#3045)
    if name not in train.TECHS and not name.endswith("_AGE") and unit in types():
        event(g, "queue", type=types()[unit], name=name, objects=at, amount=1)
    else:
        event(g, "research", technology=name.replace("_", " ").title(), objects=at)


def trained(g, uuid):
    """A unit of a queue appears (train.tick): it takes the next ID."""
    uuid = getattr(uuid, "uuid", uuid)                                 # a gather.Villager
    if getattr(g, "record", None) is not None and isinstance(uuid, str):
        g.record.id(uuid)


def aged(g, name):
    """An age research is complete (train.research)."""
    if name.endswith("_AGE"):
        event(g, "age", age=name)


def ordered(g, kind, units, cell=None, target=None):
    """A move order to the block cell (x, z) or an attack order on the unit or building target (UUID, Gather.click)."""
    if getattr(g, "record", None) is None or not units:
        return
    data = {"objects": [g.record.id(u) for u in sorted(units)]}
    if cell is not None:
        data["tile"] = [round((cell[0] + 0.5) / g.map.T, 3), round((cell[1] + 0.5) / g.map.T, 3)]
    if target is not None:
        data["target"] = g.record.id(target)
        if target in g.record.rects:                                   # a building: the tile of its middle (#3004)
            data["tile"] = tile(g, g.record.rects[target])
    event(g, kind, **data)


def load(path):
    """(refs {key: ID}, timeline) of a recorded file: the timeline in time order."""
    refs, timeline = {}, []
    with open(path) as f:
        for line in f:
            if line.strip():
                d = json.loads(line)
                refs.update(d["refs"]) if "refs" in d else timeline.append(d)
    return refs, sorted(timeline, key=lambda e: e["time"])


def apply(data, path):
    """aoe2mc.json data with the timeline of the recorded file (--replay-file): the start objects get the IDs of the
    record ("ref"), and aoe2mc.name_timeline names the new objects, as the converter does for a recorded game."""
    refs, timeline = load(path)
    objects = [dict(o) for o in data["objects"]]
    for o in objects:
        if (k := start_key(o)) in refs:
            o["ref"] = refs[k]
    aoe2mc.name_timeline(objects, timeline)
    return dict(data, objects=objects, timeline=timeline)
