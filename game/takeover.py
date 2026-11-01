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


def site(name, player, rect, progress=1.0):
    """A construction site (build.place form) of a building of the replay: the world has its blocks. A building
    that its builders still build has the progress of their build."""
    return {"name": name, "player": player, "footprint": tuple(rect), "commands": [], "sent": 0, "progress": progress,
            "paid": True, "ring": {}, "under": {}, "done": progress >= 1}


def building(r, t):
    """The progress of each footprint that builders of the replay build at game time t (ms): the part of the build
    time of its first builder that passed."""
    out = {}
    for i, (due, _) in r.builds.items():
        if i in r.raising and due > t:
            rect, start = r.raising[i]
            out[tuple(rect)] = max(out.get(tuple(rect), 0.0), min(0.99, max(0.0, (t - start) / max(1, due - start))))
    return out


def jobs(r, p, t, walkers):
    """The orders of the villagers of player p (savegame.orders form): a gatherer of the replay walks to its resource
    tile, a builder to its site, a unit in a garrison keeps its resource tile; the others are idle."""
    out = {u: villager(pos) for u, (_, pos) in walkers.items()}
    for i, v in r.units.items():
        if v.uuid not in out or getattr(v, "player", None) != p:
            continue
        job = out[v.uuid]
        if i in r.builds and i in r.raising and r.builds[i][0] > t:
            job.update(state="to_site", site=list(r.raising[i][0]))
        elif (i in r.working or i in r.arriving) and v.tree is not None:
            job.update(state="to_tree", tree=list(v.tree), res=v.res)
        elif r.work.get(i):                                            # inside a building: it goes back after it
            job.update(tree=list(r.work[i]), res=v.res)
    return out


def queues(r, p, t):
    """The queue of each building of player p at game time t (ms), as train.queue makes it: the units and the
    researches in production, the first one with the part of its time that passed. The record paid them."""
    import replay
    import train
    rects = {s[0]: tuple(s[3]) for s in r.starts if s[1] == p and s[0] is not None} | dict(r.ids)
    out = {}
    for end, e, b in sorted(r.trainings, key=lambda x: x[0]):
        if e.get("player") != p or not e["time"] <= t < end or b not in rects:
            continue
        if e["kind"] == "queue":
            name = e.get("name")
            start = end - replay.aoe2mc.train_ms(name) if name in train.COSTS else end
        else:
            n = e.get("technology")
            name, start = replay.TECHS.get(n, n), max(e["time"], end - replay.RESEARCH_S.get(n, 0) * 1000)
        if name not in train.COSTS and name not in train.TECHS:
            continue
        q = out.setdefault(rects[b], [])
        q.append({"name": name, "progress": 0.0 if q else round(min(1, max(0, (t - start) / max(1, end - start))), 3),
                  "player": p})
    return out


def player(r, p, t=0):
    """The state of player p of the Replay r at game time t (ms) (savegame.dump form of one player), with the orders
    of its units (#5453)."""
    us = live_units(r, p)
    ids = {v.uuid: i for i, v in r.units.items()}
    progress = building(r, t)
    soldiers = {u: n for u, (n, _) in sorted(us.items()) if gather.soldier(n)}
    walkers = {u: x for u, x in sorted(us.items()) if u not in soldiers}
    T = r.T
    return {"stock": {k: max(0, math.floor(v)) for k, v in sorted(r.resources(p).items())},
            "spare": {}, "seconds": {}, "repeats": {}, "pop": r.pop.get(p, 0), "techs": techs(r, p),
            "queues": savegame.pack(queues(r, p, t)), "trained": savegame.pack({}), "rally": savegame.pack({}),
            "sites": savegame.pack([site(n, q, rect, progress.get(tuple(rect), 1.0)) for q, n, rect in sorted(r.placed) if q == p]),
            "soldiers": savegame.pack(soldiers),
            "units": savegame.pack([{"kind": "unit", "name": n, "player": p, "uuid": u,
                                     "tile": [math.floor(pos[0]) / T, math.floor(pos[2]) / T]}
                                    for u, (n, pos) in walkers.items()]),
            "villagers": jobs(r, p, t, walkers),
            "farmers": [], "groups": {}, "ships": {},
            "stances": {u: s for u, i in sorted(ids.items()) if u in us and (s := r.stances.get(i, "aggressive"))
                        != "aggressive"},
            "garrisons": sorted([list(rect), sorted(r.units[i].uuid for i in inside if i in r.units)]
                                for rect, inside in r.garrisons.items()
                                if any(i in r.units and r.units[i].uuid in us for i in inside))}


ATTACK = 120                                                           # AoE2 seconds after the takeover (#5452)


def bot(r, p, t, difficulty="standard"):
    """The savegame.BOT fields of the bot that plays player p after a takeover at game time t (ms) (#5452): its clock
    goes on from t, and its first attack comes ATTACK seconds after t, on the first enemy of the record's teams."""
    import run  # run imports replay: import it late
    s = t / 1000
    return {"time": s, "charged": False, "attack": s + ATTACK, "foe": run.bot_foe(r.data["players"], p),
            "difficulty": difficulty}


def state(r, t=None, taken=1, difficulty="standard"):
    """The savegame.dump dict of the Replay r at game time t (ms; None: the time of its controls): the stock, the
    technologies, the population, the units and the done buildings of each player of the record, and the game time.
    Each player but `taken` (the Minecraft player) gets the state of its bot (#5452); difficulty: the --ai-difficulty
    setting (a comma list: one level per bot in seat order, bot.level_of).
    The same replay at the same time gives the same dict (sorted keys and lists)."""
    t = (getattr(r, "control", None) or {}).get("time", 0) if t is None else t
    ps = sorted(int(k) for k in r.data.get("players") or {} if int(k))
    import bot as ai
    seats = {p: ai.level_of(difficulty, k) for k, p in enumerate(q for q in ps if q != taken)}
    d = {"players": {str(p): player(r, p, t) | ({"bot": bot(r, p, t, seats[p])} if p in seats else {}) for p in ps},
         "game_time": round(t / 1000, 3)}
    return json.loads(json.dumps(d, sort_keys=True))                   # the JSON form: sorted keys, no tuples


def write(game, r, saves, t=None, taken=1, difficulty="standard"):
    """Save the replay of game at its time: a copy of the world after `save-all flush` (run.save) and state(r) next to
    it (savegame.write). Returns the save folder."""
    import run  # run imports replay: import it late
    copy = run.save(game)
    world = os.path.join(tempfile.mkdtemp(dir=os.path.dirname(copy)), os.path.basename(os.path.normpath(game.world)))
    os.rename(copy, world)                                             # the save takes the name of the world
    try:
        return savegame.write(saves, world, state(r, t, taken, difficulty))
    finally:
        shutil.rmtree(os.path.dirname(world), ignore_errors=True)
