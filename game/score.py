"""
The AoE2 score of each player in the game program (#2355, epic #2263): the sum of four parts (AoE2 wiki, "Score",
section Age of Empires II), for the victory settings "Score" and "Time Limit".
- Military: 20 % of the cost of the enemy units and buildings that the player destroyed. The Python side does not know
  the killer of a unit, so the cost of a fallen unit goes to its rivals in equal parts (exact in a game of two sides).
  A building falls after an attack order of its Gather (gather.Gather.fall): that Gather gets it.
- Economy: 10 % of the resources of the player and of its tributes (diplomacy.send), and 20 % of the cost of its live
  units and standing buildings, not the castles and wonders.
- Technology: 20 % of the cost of the researched technologies and ages, not the free ones of the start age (AoE2: "do
  not count"), and 10 points for each 1 % of the explored map (#2396): explore() adds the tiles in the line of sight of
  the own units and buildings (Gather.seen_tiles) to g.explored of each Gather (the people and the bots) each LOOK
  seconds, with the positions of all units in one `aoe where` (Gather.where).
- Society: 20 % of the cost of the castles and wonders that the player built (the key "society" of data/replay.jsonl).
The costs are the AoE2 costs (train.COSTS, build.COSTS), without the civilization bonuses.
Minecraft feature: a scoreboard. Each person sees one line for each player in its resource sidebar (g.board), with
the commands only when a score changes.

    score.fallen(g, dead)    # train.census: the own units that died since the last count
    score.razed(g, uuid)     # gather.Gather.fall: the target of the fallen building
    score.tick(g)            # gather.Gather.run: the explored tiles each LOOK seconds, the score each EVERY seconds
"""
import json

import build
import fog
import table
import train

EVERY = 5.0          # seconds between two counts
LOOK = 1.0           # seconds between two updates of the explored tiles (#2396)
SOCIETY = {r["name"] for r in table.load("replay.jsonl") if r.get("society")}   # castles and wonders (#1086)
PARTS = ("military", "economy", "technology", "society")


def value(cost):
    """The sum of the resources of a cost {resource: amount}."""
    return sum(cost.values())


def worth(name):
    """The AoE2 cost value of unit, technology or building name (census names a villager VILLAGER)."""
    return value(train.COSTS.get(name + "_MALE" * (name == "VILLAGER")) or build.COSTS.get(name, {}))


def fallen(g, dead):
    """Keep the dead own units ({uuid: AoE2 name}) of g: they are no longer worth points, and their rivals get them."""
    vars(g).setdefault("losses", {}).update(dead)


def razed(g, uuid):
    """Keep the enemy building with target uuid that fell after an attack order of g."""
    vars(g).setdefault("razed", {})[uuid] = g.fort_names.get(uuid, "")


def explore(g):
    """Add the tiles in sight of the own units and buildings of each Gather of the game of g to its set explored, at
    most each LOOK seconds. A destroyed building of the map still sees, as in fog.update with alive None."""
    if g.clock() < vars(g).get("explore_at", 0.0):
        return
    g.explore_at = g.clock() + LOOK
    sides = fog.gathers(g)
    pos = g.where({u for h in sides for u in (*h.villagers, *h.soldiers)})
    for h in sides:
        vars(h).setdefault("explored", set()).update(h.seen_tiles(pos))


def tiles(g):
    """The tiles of the map of g."""
    return (g.data.get("map_size") or g.map.n // g.map.T) ** 2


def buildings(g, gone):
    """The standing buildings of g (AoE2 name, built by the player): the ones of the map and the complete construction
    sites whose target uuid is not in gone. A start building that fell (g.ruins: deleted or razed) does not stand."""
    import combat  # combat imports gather, gather this module
    import ruins
    out = [(o["name"], False) for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player
           and "footprint" in o and combat.target_uuid(o["footprint"]) not in gone and not ruins.fallen(g, o)]   # #3736
    return out + [(s["name"], True) for s in g.sites if s.get("done") and s["player"] == g.player
                  and combat.target_uuid([s["footprint"][i] for i in (0, 2, 1, 3)]) not in gone]


def points(g, sides=None):
    """The points of each part for each side of the game of g (or of the Gathers sides): {player: {part: points}}."""
    sides = sides or fog.gathers(g)
    gone = {u for h in sides for u in vars(h).get("razed", {})}
    out = {}
    for h in sides:
        lost = vars(h).get("losses", {})
        rivals = [o for o in sides if not allied(o, h)]
        kills = sum(worth(n) for n in vars(h).get("razed", {}).values()) \
            + sum(worth(n) / len([r for r in sides if not allied(r, o)])
                  for o in rivals for n in vars(o).get("losses", {}).values())
        units = [*("VILLAGER" for u in h.villagers if u not in lost), *(n for u, n in h.soldiers.items() if u not in lost)]
        built = buildings(h, gone)
        given = vars(h).get("given", set())
        techs = [t for t in h.techs if t not in given] + [t for t, n in h.repeats.items() for _ in range(n)]
        out[h.player] = {
            "military": 0.2 * kills,
            "economy": 0.1 * (sum(h.stock.values()) + sum(value(t) for t in vars(h).get("tributes", {}).values()))
            + 0.2 * (sum(worth(n) for n in units) + sum(worth(n) for n, _ in built if n not in SOCIETY)),
            "technology": 0.2 * sum(worth(t) for t in techs) + 10 * 100 * len(vars(h).get("explored", ())) / tiles(h),
            "society": 0.2 * sum(worth(n) for n, own in built if own and n in SOCIETY)}
    return out


def allied(a, b):
    """The Gathers a and b are on one side (gather.allied, #1313)."""
    from gather import allied  # gather imports this module
    return allied(a.players, a.player, b.player)


def total(parts):
    """The score: the sum of the parts, as a whole number."""
    return int(sum(parts.values()))


def tick(g):
    """Count the score of each player each EVERY seconds and show the changed ones in the sidebar of each person."""
    if g.ended:
        return
    explore(g)
    if g.clock() < vars(g).get("score_at", 0.0):
        return
    g.score_at = g.clock() + EVERY
    scores = {n: total(p) for n, p in points(g).items()}
    for h in [g, *g.peers]:                                         # the people: a bot has no sidebar to see
        for n, s in sorted(scores.items()):
            name = f"Score{n}"                                      # a holder name has no space (#990)
            if h.shown.get(name) == s:
                continue
            if name not in h.shown:
                h.command(f"scoreboard players display name {name} {h.board} {json.dumps(f'Score of player {n}')}")
            h.shown[name] = s
            h.command(f"scoreboard players set {name} {h.board} {s}")
