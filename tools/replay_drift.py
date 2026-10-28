#!/usr/bin/env python3
"""
Measure how far the units of a live replay on Paper are from their replay positions (#813).

Usage:
    python3 tools/replay_drift.py samples/de-64.3.aoe2record [--speed 4] [--until 10:00] [--log OUT.jsonl] [--server-log OUT.log]
    python3 tools/replay_drift.py WORLD ...                    # a converted world of a record (the tool copies it;
                                                               # it stops on a world that a game saved, #2667)
    python3 tools/replay_drift.py --read OUT.jsonl             # only print the table of a log

The tool converts the record (or copies the world: the game saves its changes there, #718), starts Paper without a
client and plays the replay with the plugin AI (`Replay(game, data, ai=True)`). Every `--every` seconds of game time it
reads the real positions of all units with one plugin command (`aoe where`) and writes one sample per unit: the entity
position, the replay position `v.pos` (the end of its leg while it walks), the blocks that the replay still walks on
that leg ("slack"), the order of the plugin and the target of the mob AI.
The table has one row per unit kind: units, median and maximum distance (blocks, without height, less the slack), "stuck" (more than
STUCK_BLOCKS from the replay position for more than STUCK_SECONDS of game time), "stray" (moved more than STRAY_BLOCKS
between two samples with no plugin order, no mob target or fight since the last sample, the same replay position, and
not nearer to it: #1169, the end of a walk or a jump to the position is no stray), "died" (the entity is gone in all later samples, the replay still has the unit: a unit that comes back did not die)
and "still" (#1139: seconds of game time between two samples with a plugin order in both, more than STUCK_BLOCKS from
the replay position in both, and less than STILL_BLOCKS of move between them: a unit that the plugin holds in place.
In #851 a plugin change held villagers for 120 s, and the other columns did not show it).
The second table (#829) has the walk speed of the units that walk behind their replay position: blocks per game second
between two samples with a plugin order in both and more than FAR_BLOCKS of distance, as a median and as a part of
the replay speed ("need": the AoE2 speed times the tile size). Use `--every 2` for it: with 10 s between two samples a
detour counts as a slow walk.
"""
import argparse
import contextlib
import io
import json
import math
import os
import re
import shutil
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path[:0] = [ROOT, HERE, os.path.join(ROOT, "game")]

STUCK_BLOCKS, STUCK_SECONDS, STRAY_BLOCKS = 4, 30, 2
FAR_BLOCKS = 20
STILL_BLOCKS = 0.3


class Done(Exception):
    """--until: the poll of Replay.run stops the replay."""


def where(game, selector):
    """uuid -> (x, y, z, order, target) of each entity of the selector: `aoe where`, page by page."""
    out, start = {}, 0
    while True:
        m = re.search(r"Where (\d+): ?(.*)", game.command(f"aoe where {selector} {start}"))
        if not m:
            raise RuntimeError("no answer of `aoe where`: is the plugin on the server?")
        for part in filter(None, m[2].split(", ")):
            u, x, y, z, o, t = part.split()
            out[u] = (float(x), float(y), float(z), o == "1", t == "1")
        start += 40
        if start >= int(m[1]):
            return out


def sample(r, now, found):
    """The samples (dicts) of the player units of Replay r at game time now (ms); found: the answer of where()."""
    import replay
    import units
    rows, due = [], {id(r.units[i]): t for i, t in r.moving.items() if i in r.units}
    for key, v in list(r.units.items()) + [(None, v) for _, v in r.new]:
        if not v.uuid or not getattr(v, "player", 0) or units.animal(getattr(v, "name", "") or ""):
            continue
        e = found.get(v.uuid)
        speed = next((s for k, s in replay.SPEEDS.items() if v.name.startswith(k)), 1.0) * r.T     # blocks per second
        rows.append({"t": int(now), "ref": key, "uuid": v.uuid, "name": v.name, "player": v.player,
                     "rx": round(v.pos[0], 2), "ry": v.pos[1], "rz": round(v.pos[2], 2), "walking": id(v) in due,
                     "slack": round(math.dist(r.at(v, now)[::2], v.pos[::2]), 2),    # the rest of its leg (#851)
                     "need": speed,
                     **({"x": e[0], "y": e[1], "z": e[2], "order": e[3], "target": e[4]} if e else {"x": None, "z": None})})
    return rows


def kind(name):
    return re.sub(r"_(MALE|FEMALE)$", "", name or "?")


def analyze(samples):
    """kind -> {units, median, max, stuck, stray, died, still}: the values of the table (see the module text)."""
    by = {}
    for s in sorted(samples, key=lambda s: s["t"]):
        by.setdefault(s["uuid"], []).append(s)
    out = {}
    for u, rows in by.items():
        k = out.setdefault(kind(rows[0]["name"]), {"units": 0, "d": [], "stuck": 0, "stray": 0, "died": 0,
                                                     "still": 0.0})
        k["units"] += 1
        far, stuck, stray, last, last_d, last_raw = None, False, False, None, 0.0, 0.0
        for s in rows:
            if s["x"] is None:
                continue
            raw = ((s["x"] - s["rx"]) ** 2 + (s["z"] - s["rz"]) ** 2) ** 0.5
            d = max(0.0, raw - s.get("slack", 0))
            k["d"].append(d)
            far = (far if far is not None else s["t"]) if d > STUCK_BLOCKS else None
            stuck |= far is not None and s["t"] - far > STUCK_SECONDS * 1000
            if last and (last["rx"], last["rz"]) == (s["rx"], s["rz"]) and not any(
                    r.get(k) for r in (last, s) for k in ("order", "target")):    # no order, no fight, no new leg
                stray |= ((s["x"] - last["x"]) ** 2 + (s["z"] - last["z"]) ** 2) ** 0.5 > STRAY_BLOCKS and \
                    raw >= last_raw          # nearer the replay position: the end of a walk (raw: the slack goes, #1333)
            if last and last.get("order") and s.get("order") and min(d, last_d) > STUCK_BLOCKS and \
                    ((s["x"] - last["x"]) ** 2 + (s["z"] - last["z"]) ** 2) ** 0.5 < STILL_BLOCKS:
                k["still"] += (s["t"] - last["t"]) / 1000              # held in place with an order
            last, last_d, last_raw = s, d, raw
        died = last is not None and rows[-1]["x"] is None   # gone in all samples after its last position (#3047)
        k["stuck"] += stuck
        k["stray"] += stray
        k["died"] += died
    for k in out.values():
        d = k.pop("d")
        k["median"], k["max"] = (round(statistics.median(d), 1), round(max(d), 1)) if d else (None, None)
        k["still"] = round(k["still"])
    return out


def walk(samples):
    """kind -> {"moves", "walk", "need", "part"}: the second table (see the module text)."""
    by, out = {}, {}
    for s in sorted(samples, key=lambda s: s["t"]):
        by.setdefault(s["uuid"], []).append(s)
    for rows in by.values():
        for a, b in zip(rows, rows[1:]):
            if a["x"] is None or b["x"] is None or not (a.get("order") and b.get("order")) or b["t"] <= a["t"] or \
                    ((a["x"] - a["rx"]) ** 2 + (a["z"] - a["rz"]) ** 2) ** 0.5 - a.get("slack", 0) <= FAR_BLOCKS:
                continue
            k = out.setdefault(kind(a["name"]), {"v": [], "need": a.get("need")})
            k["v"].append(((b["x"] - a["x"]) ** 2 + (b["z"] - a["z"]) ** 2) ** 0.5 / ((b["t"] - a["t"]) / 1000))
    for k in out.values():
        v = k.pop("v")
        k["moves"], k["walk"] = len(v), round(statistics.median(v), 2)
        k["part"] = round(k["walk"] / k["need"], 2) if k["need"] else None
    return out


def walk_table(stats):
    rows = [("Unit", "Moves", "Walk", "Need", "Part")] + [
        (n, k["moves"], k["walk"], k["need"], "-" if k["part"] is None else f"{k['part']:.0%}")
        for n, k in sorted(stats.items(), key=lambda kv: (-kv[1]["moves"], kv[0]))]
    w = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(str(c).ljust(w[0]) if i == 0 else str(c).rjust(w[i]) for i, c in enumerate(r))
                     for r in rows)


def table(stats):
    rows = [("Unit", "Units", "Median", "Max", "Stuck", "Stray", "Died", "Still")] + [
        (n, k["units"], k["median"], k["max"], k["stuck"], k["stray"], k["died"], k.get("still", 0))
        for n, k in sorted(stats.items(), key=lambda kv: (-kv[1]["units"], kv[0]))]
    w = [max(len(str(r[i])) for r in rows) for i in range(len(rows[0]))]
    return "\n".join("  ".join(str(c).ljust(w[0]) if i == 0 else str(c).rjust(w[i]) for i, c in enumerate(r))
                     for r in rows)


def keep_log(game, path):
    """Copy the server log of game to path before run.Game deletes its folder (#2464: the "no path" lines)."""
    log = os.path.join(game.folder, "logs", "latest.log")
    if os.path.isfile(log):
        shutil.copyfile(log, path)


def played(world, data, near=2):
    """The object IDs of the start units whose entity in world stands more than near blocks (without height) from
    its tile in aoe2mc.json: a world that a game saved stands at the place where that game stopped (#2667: eagle scout
    1665 of de-64.3 stood at its 11:55 place, 366 blocks away, and the drift of a later run was wrong)."""
    import uuid
    import world_reader
    pos = {}
    for e in world_reader.World(world).entities():
        if "UUID" in e:
            a = [int(v) & 0xFFFFFFFF for v in e["UUID"]]
            pos[str(uuid.UUID(int=a[0] << 96 | a[1] << 64 | a[2] << 32 | a[3]))] = [float(v) for v in e["Pos"]]
    T = data["tile_size"]
    return [o["ref"] for o in data["objects"] if o["kind"] == "unit" and o.get("ref") is not None
            and o.get("uuid") in pos and math.dist((pos[o["uuid"]][0], pos[o["uuid"]][2]),
                                                    (o["tile"][0] * T, o["tile"][1] * T)) > near]


def measure(src, speed=4.0, until=None, every=10, log=None, version=None, server_log=None):
    """Play the replay of src (a record or a converted world) on Paper; returns the samples. server_log: copy the
    server log to this file at the end, also after an error."""
    import aoe2mc
    import mc_check
    import replay
    import run
    samples = []
    with tempfile.TemporaryDirectory() as tmp:
        world = os.path.join(tmp, "DriftWorld")
        if os.path.isdir(src):
            shutil.copytree(src, world)
        else:
            with contextlib.redirect_stdout(io.StringIO()):
                aoe2mc.convert(src, world)
        with open(os.path.join(world, "aoe2mc.json")) as f:
            data = json.load(f)
        if os.path.isdir(src) and (moved := played(world, data)):
            raise SystemExit(f"{src}: a game saved this world, {len(moved)} start units are not at their tile "
                             f"(object IDs {moved[:5]}). Convert the record again, or give the record.")
        with run.Game(world, version or mc_check.DEFAULT_VERSION) as game:
            game.forceload()
            import combat
            combat.setup(game, data)
            r = replay.Replay(game, data, game.version, ai=True)
            due = [0]

            def poll(control):
                now = control["time"]
                if until is not None and now >= until:
                    raise Done
                if now >= due[0]:
                    r.grid()
                    rows = sample(r, now, where(game, f"@e[tag={replay.COUNTED}]"))
                    samples.extend(rows)
                    if log:
                        log.write("".join(json.dumps(s) + "\n" for s in rows))
                        log.flush()
                    due[0] = now + every * 1000
                    m, s = divmod(int(now) // 1000, 60)
                    print(f"{m:02d}:{s:02d} {len(rows)} units", file=sys.stderr)

            try:
                r.run(speed, bar=True, poll=poll, log=None)     # bar: as run.py --replay (tags, census)
            except Done:
                pass
            finally:
                if server_log:
                    keep_log(game, server_log)
    return samples


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0].strip(),
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", nargs="?", help="a record (.aoe2record) or a converted world of a record")
    ap.add_argument("--speed", type=float, default=4.0, help="times the game speed (default 4, #718)")
    ap.add_argument("--until", metavar="MM:SS", help="stop at this game time")
    ap.add_argument("--every", type=float, default=10, help="seconds of game time between two samples (default 10)")
    ap.add_argument("--log", metavar="FILE", help="write the samples (JSON lines)")
    ap.add_argument("--read", metavar="FILE", help="only print the table of a log")
    ap.add_argument("--version", help="Minecraft version of the server")
    ap.add_argument("--server-log", metavar="FILE", help="copy the server log to this file at the end (#2464)")
    a = ap.parse_args(argv)
    if a.read:
        with open(a.read) as f:
            samples = [json.loads(line) for line in f if line.strip()]
    elif a.src:
        import aoe2mc
        until = aoe2mc.game_time(a.until) if a.until else None
        with contextlib.ExitStack() as stack:
            log = stack.enter_context(open(a.log, "w")) if a.log else None
            samples = measure(a.src, a.speed, until, a.every, log, a.version, a.server_log)
    else:
        ap.error("give a record, a world or --read FILE")
    print(table(analyze(samples)))
    print()
    print(walk_table(walk(samples)))


if __name__ == "__main__":
    main()
