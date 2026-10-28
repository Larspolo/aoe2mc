"""
The AoE2 score of each player in the game program (#2355, epic #2263): the sum of four parts (AoE2 wiki, "Score",
section Age of Empires II), for the victory settings "Score" and "Time Limit".
- Military: 20 % of the cost of the enemy units and buildings that the player destroyed. The Python side does not know
  the killer of a unit, so the cost of a fallen unit goes to its rivals in equal parts (exact in a game of two sides).
  A building falls after an attack order of its Gather (gather.Gather.fall): that Gather gets it.
- Economy: 10 % of the resources of the player and of its tributes (diplomacy.send), and 20 % of the cost of its live
  units and standing buildings, not the castles and wonders.
- Technology: 20 % of the cost of the researched technologies and ages, not the free ones of the start age (AoE2: "do
  not count"). The 10 points for each 1 % of the explored map are not in it: the game program does not keep the
  explored tiles.
- Society: 20 % of the cost of the castles and wonders that the player built (the key "society" of data/replay.jsonl).
The costs are the AoE2 costs (train.COSTS, build.COSTS), without the civilization bonuses.
Minecraft feature: a scoreboard. Each person sees one line for each player in its resource sidebar (g.board), with
the commands only when a score changes.

    score.fallen(g, dead)    # train.census: the own units that died since the last count
    score.razed(g, uuid)     # gather.Gather.fall: the target of the fallen building
    score.tick(g)            # gather.Gather.run: once each EVERY seconds
"""
import json

import build
import fog
import table
import train

EVERY = 5.0          # seconds between two counts
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


def buildings(g, gone):
    """The standing buildings of g (AoE2 name, built by the player): the ones of the map and the complete construction
    sites whose target uuid is not in gone."""
    import combat                                                   # combat imports gather, gather this module
    out = [(o["name"], False) for o in g.data["objects"] if o["kind"] == "building" and o["player"] == g.player
           and "footprint" in o and combat.target_uuid(o["footprint"]) not in gone]
    return out + [(s["name"], True) for s in g.sites if s.get("done") and s["player"] == g.player
                  and combat.target_uuid([s["footprint"][i] for i in (0, 2, 1, 3)]) not in gone]


def points(g):
    """The points of each part for each side of the game of g: {player: {part: points}}."""
    sides = fog.gathers(g)
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
            "technology": 0.2 * sum(worth(t) for t in techs),
            "society": 0.2 * sum(worth(n) for n, own in built if own and n in SOCIETY)}
    return out


def allied(a, b):
    """The Gathers a and b are on one side (gather.allied, #1313)."""
    from gather import allied                                       # gather imports this module
    return allied(a.players, a.player, b.player)


def total(parts):
    """The score: the sum of the parts, as a whole number."""
    return int(sum(parts.values()))


def tick(g):
    """Count the score of each player each EVERY seconds and show the changed ones in the sidebar of each person."""
    if g.ended or g.clock() < vars(g).get("score_at", 0.0):
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
