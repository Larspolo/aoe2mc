"""Take over a live replay (epic #5448): the state of each player of the replay at its time becomes a game save that
`run.py WORLD --play --load SAVE` loads (#5449).

The world folder is the save (Minecraft feature: the blocks and the mobs with their UUIDs); only the program state goes
into `savegame.json`, in the form of `savegame.dump`, with only the keys that `savegame.load` reads.
"""
import json
import math
import os
import shutil
import tempfile

import gather
import savegame


def techs(r, p):
    """The technologies of player p: the researches of the record (Replay.learned) and the ages that it reached, as the
    names of train.TECHS."""
    import replay  # replay imports build, which imports gather: import it late
    names = {n for _, n in r.learned.get(p, ()) if n in replay.TECH_ROW}
    return sorted(names | set(r.reached.get(p, {})))


def live_units(r, p):
    """The live units of player p, uuid -> (name, (x, y, z)): the units of the replay (also the spawned ones with no
    object ID yet) and the start units with no object ID (the record never names them). No animals."""
    import units  # aoe2mc/units.py: replay puts the root folder on the path
    m, T, out = r.grid(), r.T, {}                                      # the first call finds the start units
    for v in [*r.units.values(), *(v for q, v in r.new if q == p)]:
        if getattr(v, "player", None) == p:
            out[v.uuid] = (v.name, tuple(v.pos))
    for o in r.data["objects"]:
        if o["kind"] == "unit" and o.get("player") == p and o.get("uuid") and o.get("ref") is None:
            x, z = o["tile"][0] * T, o["tile"][1] * T
            out.setdefault(o["uuid"], (o["name"], (x, float(m.y(int(x), int(z)) or 0), z)))
    return {u: x for u, x in out.items() if not units.animal(x[0])}


def villager(pos):
    """The orders of an idle villager at pos (savegame.orders form): after the load it waits for an order."""
    return {"state": "idle", "load": 0, "res": "wood", "job": None, "lap": 0, "prey": None, "task": None,
            "pos": list(pos), "tree": None, "site": None, "goal": None, "repair": None}


def site(name, player, rect):
    """A done construction site (build.place form) of a building of the replay: the world has its blocks."""
    return {"name": name, "player": player, "footprint": tuple(rect), "commands": [], "sent": 0, "progress": 1.0,
            "paid": True, "ring": {}, "under": {}, "done": True}


def player(r, p):
    """The state of player p of the Replay r (savegame.dump form of one player)."""
    us = live_units(r, p)
    soldiers = {u: n for u, (n, _) in sorted(us.items()) if gather.soldier(n)}
    walkers = {u: x for u, x in sorted(us.items()) if u not in soldiers}
    T = r.T
    return {"stock": {k: max(0, math.floor(v)) for k, v in sorted(r.resources(p).items())},
            "spare": {}, "seconds": {}, "repeats": {}, "pop": r.pop.get(p, 0), "techs": techs(r, p),
            "queues": savegame.pack({}), "trained": savegame.pack({}), "rally": savegame.pack({}),
            "sites": savegame.pack([site(n, q, rect) for q, n, rect in sorted(r.placed) if q == p]),
            "soldiers": savegame.pack(soldiers),
            "units": savegame.pack([{"kind": "unit", "name": n, "player": p, "uuid": u,
                                     "tile": [math.floor(pos[0]) / T, math.floor(pos[2]) / T]}
                                    for u, (n, pos) in walkers.items()]),
            "villagers": {u: villager(pos) for u, (_, pos) in walkers.items()},
            "farmers": [], "stances": {}, "groups": {}, "garrisons": [], "ships": {}}


def state(r, t=None):
    """The savegame.dump dict of the Replay r at game time t (ms; None: the time of its controls): the stock, the
    technologies, the population, the units and the done buildings of each player of the record, and the game time.
    The same replay at the same time gives the same dict (sorted keys and lists)."""
    t = (getattr(r, "control", None) or {}).get("time", 0) if t is None else t
    ps = sorted(int(k) for k in r.data.get("players") or {} if int(k))
    d = {"players": {str(p): player(r, p) for p in ps}, "game_time": round(t / 1000, 3)}
    return json.loads(json.dumps(d, sort_keys=True))                   # the JSON form: sorted keys, no tuples


def write(game, r, saves, t=None):
    """Save the replay of game at its time: a copy of the world after `save-all flush` (run.save) and state(r) next to
    it (savegame.write). Returns the save folder."""
    import run  # run imports replay: import it late
    copy = run.save(game)
    world = os.path.join(tempfile.mkdtemp(dir=os.path.dirname(copy)), os.path.basename(os.path.normpath(game.world)))
    os.rename(copy, world)                                             # the save takes the name of the world
    try:
        return savegame.write(saves, world, state(r, t))
    finally:
        shutil.rmtree(os.path.dirname(world), ignore_errors=True)
