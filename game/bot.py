"""A bot plays a player of the game program without a human (#397). First step (#856): its villagers gather food,
wood, gold and stone. It trains villagers up to a number, then soldiers at its military buildings (#858).

The bot has its own gather.Gather for its player. That Gather gets no clicks, and it writes its resources to its own
objective (Gather.board), which no sidebar shows: the sidebar of player 1 does not change. Each step sends the idle
villagers to the nearest source of the resource with the largest gap to SHARE. The villagers walk with the plugin
(`aoe moveto`) on Paper, as the villagers of player 1.

Build (#857): a house when the population is 2 below the limit, then the buildings of ORDER when the bot has their
cost. One villager builds each site (an idle one, else the nearest), next to the source of the building (NEAR) or
the town center. An unfinished site without a working builder gets a new one (#1121). Each building of ORDER once, as the first buildings of an AoE2 build order.

Army shares (#1049): when the bot has its villager number and a building that trains a soldier, the shares follow the
cost of that soldier (train.COSTS), with WOOD for farms and houses; stone gets no new villagers. Each step moves at
most one working villager from a resource above its share to the resource most below its share, as an AoE2 bot does.

Attack (#859): until the game time `attack` (AoE2 seconds) the soldiers stay at their buildings. Then each soldier
without a live target attacks the nearest unit of player `foe`, else its nearest building, with the mob AI of the
plugin (`ai.attack`, `aoe attack`). A soldier gets a new target when its target dies, and when it comes no nearer to
its target and does no damage to it for STALL seconds (#3441): AoE2 units that cannot reach a target take another one.

Difficulty (#2661, decision #2648): the AoE2 DE setting "AI difficulty" (run.py --ai-difficulty) is one line of
game/data/difficulty.jsonl (LEVELS): "gather" times the work rate of the bot villagers, "attack" times the time of the
first attack, "soldiers" in the first wave. AoE2 does not publish what each level changes: the values are a guess.

Defense (#3399): a predator in the sight of a bot villager gets the hunt order of the DEFENDERS nearest villagers, as
the AoE2 AI does. After the kill they go back to their last resource and source.
"""
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai  # noqa: E402
import build  # noqa: E402
import combat  # noqa: E402
import garrison  # noqa: E402
import gather  # noqa: E402
import herd  # noqa: E402
import table  # noqa: E402
import train  # noqa: E402

SHARE = {"food": 0.4, "wood": 0.3, "gold": 0.2, "stone": 0.1}     # the villagers on each resource (a simple AoE2 bot)
WOOD = 0.2                                                         # the wood share for farms and houses with an army
QUEUED = 2                                                         # units in the queue of each building of the bot
# The build order after the houses (the key "bot" of data/build.jsonl), and the resource that a drop site goes next to
FAR = 12                                                           # tiles from a drop site to its sources (remote)
ORDER = tuple(r["name"] for r in sorted((r for r in build.ROWS if "bot" in r), key=lambda r: r["bot"]))
NEAR = {r["name"]: r["near"] for r in build.ROWS if "near" in r}
HOUSE_GAP = 2                                                      # a new house at this many units below the limit
ATTACK = 600.0                                                     # AoE2 seconds: the first attack at 10:00
LOOK = 2.0                                                         # AoE2 seconds between two looks for targets
RETRY = 60.0                                                       # AoE2 seconds: try a source with no path again
STALL = 30.0                                                       # AoE2 seconds with no step nearer and no damage
DEFENDERS = 3                                                      # villagers that attack one predator
LEVELS = {r["name"]: r for r in table.load("difficulty.jsonl")}    # "AI difficulty", in the order of the AoE2 lobby


def box_gap(box, p):
    """Blocks from position p to the side of building box (x0, y0, z0, x1, y1, z1) on the ground; 0 inside it."""
    return math.hypot(max(box[0] - p[0], 0, p[0] - box[3] - 1), max(box[2] - p[2], 0, p[2] - box[5] - 1))


class Bot:
    order = ORDER                                                      # the buildings after the houses (build)

    def __init__(self, game, data, player=2, share=None, villagers=20, attack=ATTACK, foe=1, group=None,
                 difficulty="standard", own=None, **kw):
        """share: the Gather of the human player. Both then use the same trees, bushes and mines.
        villagers: the bot trains villagers up to this number, then soldiers.
        attack: the game time (AoE2 seconds) of the first attack on player foe, times the "attack" of the difficulty.
        group: the soldiers of the first wave (default: the "soldiers" of the difficulty); until then they stay at
        their buildings (#1051). difficulty: a name of LEVELS (#2661).
        own: the Gather of a person that the bot plays for (tools/play_check.py drives player 1, #3324): its run()
        steps it, so the bot only gives orders (orders()), and share is the Gather of the foe."""
        level = LEVELS[difficulty]
        self.g = own or gather.Gather(game, data, player=player, **kw)
        self.g.chop = {k: s / level["gather"] for k, s in self.g.chop.items()}   # seconds per unit: work_time
        self.villagers, self.attack, self.foe, self.share = villagers, attack * level["attack"], foe, share
        self.group = level["soldiers"] if group is None else group
        self.charged = False                                           # the wave attacks: new soldiers join it
        self.time, self.looked, self.targets = 0.0, -LOOK, {}          # AoE2 seconds of the game, soldier -> target
        self.chase = {}                                                # soldier -> (target, gap, hit points, since)
        self.lost = {}                                                 # soldier -> {target it gave up: its position}
        self.nobody = f"@a[tag=aoe2mc.bot{player}]"                     # the texts of the queues go to no player
        if own is None:                                                # conquest.main: a Gather with a share is a bot
            self.g.share = share                                       # monk.heresy: the techs of the human player
        if share and own is None:
            self.g.map.trees, self.g.map.bushes, self.g.map.mines = share.map.trees, share.map.bushes, share.map.mines
            self.g.relics = share.relics                                # one list: each relic exists once (#3116)
        self.failed = {}                                               # sources that a villager could not reach -> time
        self.sent = {}                                                 # villager -> the tile that go() sent it to
        self.sides = (None, {})                                        # (own and foe places, {tile: at home}) (#1810)
        self.g.home = self.home                                        # the next bush or mine of Gather.nearest too
        self.guarded = -LOOK                                           # AoE2 seconds of the last look for predators
        self.defense = {}                                              # villager -> (predator, last res, last tree)
        self.g.work_on = False                                         # the bot gives the tasks after a build or a tree (#3271)

    def setup(self):
        """Find the villagers of the player (the entities must be loaded) and make the objective of the resources."""
        g = self.g
        g.command(f'scoreboard objectives add {g.board} dummy "Player {g.player}"')
        g.show_stock()                                                 # spending and gathering add to these (#2833)
        for o in g.units:
            if pos := g.pos(o["uuid"]):
                g.villagers[o["uuid"]] = gather.Villager(o["uuid"], pos)
        return self

    def sources(self, res):
        """{tile: amount} of the trees, the fruit bushes and the own farms without a farmer, or the mines of res."""
        m = self.g.map
        if res == "food":                                              # a farm takes one farmer (Gather.send)
            return self.home({**m.bushes, **{t: k for t, k in m.farms.items() if t in m.own_farms and t not in self.g.farmers}})
        return self.home(m.trees if res == "wood" else m.mines[res], far=True)

    def home(self, sources, far=False):
        """The sources {tile: amount} whose tile is not nearer to a building of the foe than to an own town center or
        drop site (#1810): an AoE2 AI gathers at its own base. Else the bot sent its villagers to the bushes next to the
        town center of the foe when its own ones were empty, and they died there; now it builds farms (build).
        far: when the base has no source left, the sources at least half the base-to-foe distance from the foe: an
        AoE2 AI builds a lumber or mining camp at the next forest or mine (#3402)."""
        g, T = self.g, self.g.map.T
        own = tuple(sorted((sum(x for x, _ in c) / len(c), sum(z for _, z in c) / len(c))
                           for r in sorted(g.map.drops) for c in g.map.drops[r] if c))
        foe = tuple(sorted({((x0 + x1) / 2, (z0 + z1) / 2) for o in g.data["objects"] if o["kind"] == "building"
                            and o["player"] == self.foe and "footprint" in o for x0, z0, x1, z1 in [o["footprint"]]} |
                           {((x0 + x1) / 2, (z0 + z1) / 2) for s in (self.share.sites if self.share else ())
                            if s["player"] == self.foe for x0, x1, z0, z1 in [s["footprint"]]}))
        if not own or not foe:
            return sources
        if self.sides[0] != (own, foe):                                # a new building: decide each tile again
            self.sides = ((own, foe), {})
        at = self.sides[1]
        for t in sources.keys() - at.keys():
            c = ((t[0] + 0.5) * T, (t[1] + 0.5) * T)
            at[t] = min(math.dist(c, p) for p in own) <= min(math.dist(c, p) for p in foe)
        kept = {t: k for t, k in sources.items() if at[t]}
        if not far or any(k > 0 for k in kept.values()):
            return kept
        half = max(min(math.dist(p, q) for q in foe) for p in own) / 2
        beyond = {t: k for t, k in sources.items()
                  if min(math.dist(((t[0] + 0.5) * T, (t[1] + 0.5) * T), q) for q in foe) >= half}
        if any(k > 0 for k in beyond.values()):
            return beyond
        return {t: k for t, k in sources.items() if k > 0}             # no source left: the next one, near the foe too (#3545)

    def step(self):
        """One tick of the gather game of the player, then the orders."""
        self.g.step()
        self.orders()

    def orders(self):
        """Orders for the idle villagers, the sites, the queues and the soldiers."""
        g = self.g
        self.defend()
        self.build()
        share = self.shares()
        work = {r: 0 for r in SHARE}
        idle = []
        for v in g.villagers.values():
            sent = self.sent.pop(v.uuid, None) if v.state not in ("idle", "to_tree") else self.sent.get(v.uuid)
            if v.state != "idle":
                work[v.res] += 1
            elif v.tree is not None and self.sources(v.res).get(v.tree, 0) > 0:
                if sent == v.tree:                                     # sent there, idle before it gathered: no path
                    self.failed[v.tree] = self.time
                    v.tree = None
                    idle.append(v)
                else:                                                  # came out of a building: back to work (#3543)
                    g.send(v.tree, {v.uuid})
                    self.sent[v.uuid] = v.tree
                    work[v.res] += 1
            else:
                idle.append(v)
        n = len(g.villagers)
        for v in sorted(idle, key=lambda v: v.uuid):
            for res in sorted(SHARE, key=lambda r: (work[r] - share[r] * n, r)):     # the largest gap first
                if self.go(v, res):
                    work[res] += 1
                    break
        self.move(share, work)
        self.recruit()
        self.time += g.tick * gather.NORMAL
        if self.time >= self.attack and self.time >= self.looked + LOOK:   # each look costs RCON commands
            self.looked = self.time
            self.fight()

    def defend(self):
        """Send the DEFENDERS nearest villagers to a predator in the sight of a bot villager (#3399). A defender whose
        predator is dead goes back to its last task: orders() sends an idle villager with a tree to that tree."""
        g = self.g
        if self.time < self.guarded + LOOK:                            # each predator costs one RCON command
            return
        self.guarded = self.time
        for u, (prey, res, tree) in sorted(self.defense.items()):
            if prey not in g.prey and (v := g.villagers.get(u)):
                del self.defense[u]
                if v.prey is None:
                    v.res, v.tree = res, tree
            elif u not in g.villagers:
                del self.defense[u]
        hunted = {p for p, *_ in self.defense.values()}
        reach = combat.sight("VILLAGER_MALE") * g.map.T
        for prey in sorted(p for p, name in g.prey.items() if gather.predator(name) and p not in hunted):
            if not (pos := g.pos(prey)):
                continue
            gap = {u: math.dist((v.pos[0], v.pos[2]), (pos[0], pos[2])) for u, v in g.villagers.items() if v.pos}
            if not gap or min(gap.values()) > reach:
                continue
            who = set(sorted(gap, key=lambda u: (gap[u], u))[:DEFENDERS])
            for u in who:
                v = g.villagers[u]
                self.defense[u] = (prey, v.res, v.tree)
            g.hunt(prey, who)

    def go(self, v, res):
        """Send villager v to the nearest source of res that has some left. False when there is none."""
        g = self.g
        full = [t for t, k in self.sources(res).items() if k > 0 and self.time - self.failed.get(t, -RETRY) >= RETRY]
        if full:
            T = g.map.T
            tile = min(full, key=lambda t: (math.dist(v.cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), t))
            g.send(tile, {v.uuid})
            self.sent[v.uuid] = tile
        return bool(full)

    def army(self):
        """The military unit that the first own training building (not a town center) trains, or None."""
        g = self.g
        return next((n for rect, name in sorted(train.homes(self.g).items()) if name != "TOWN_CENTER"
                     for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS
                     and not build.locked(g, n)), None)

    def shares(self):
        """SHARE, or the shares of the army (#1049) when the bot has its villager number and trains a soldier."""
        unit = len(self.g.villagers) >= self.villagers and self.army()
        if not unit:
            return SHARE
        cost = train.price(self.g, unit)
        total = sum(cost.values())
        return {r: (WOOD if r == "wood" else 0) + (1 - WOOD) * cost.get(r, 0) / total for r in SHARE}

    def move(self, share, work):
        """Move one working villager from the resource most above its share to the resource most below it, when the
        first has a whole villager too many: then the move never goes back. Food with no free farm: to wood, the cost
        of the next farm (#1083)."""
        g, n = self.g, len(self.g.villagers)
        gap = {r: work[r] - share[r] * n for r in SHARE}
        low = min(SHARE, key=lambda r: (gap[r], r))
        if gap[low] >= 0:
            return
        if low == "food" and not any(k > 0 for k in self.sources("food").values()):
            low = "wood"
        high = max((r for r in SHARE if r != low), key=lambda r: (gap[r], r))
        if gap[high] < 1:
            return
        busy = sorted(u for u, v in g.villagers.items() if v.state != "idle" and v.res == high and v.site is None)
        for v in [g.villagers[u] for u in busy[:1]]:                   # a builder stays at its site
            if self.go(v, low):
                work[high] -= 1
                work[low] += 1

    def fight(self):
        """Send each soldier without a live target to the nearest unit of the foe in reach and in the sight of the bot
        (#2050), else to its nearest building. A wave starts with self.group soldiers; when all of it is dead, the next wave waits for a full group again (#1051)."""
        g = self.g
        mine = g.positions(sorted(u for u, n in g.soldiers.items() if combat.stats(n).attack))   # a dead soldier
                                                                       # is not in it, a transport ship has no attack
        self.charged = len(mine) >= self.group or self.charged and bool(mine)
        if not self.charged or self.foe is None:                      # no enemy: no attack (#3107)
            return
        inside = garrison.inside(self.share) if self.share else set()  # a unit in a building is no target (#3429)
        live = {t for t in set(self.targets.values()) if t not in inside and "passed" in g.command(f"execute if entity {t}")}
        self.targets = {u: t for u, t in self.targets.items() if u in mine and t in live}
        self.stalled(mine)
        if not mine.keys() - {u for u, t in self.targets.items() if t not in g.forts}:
            return                                                     # all soldiers fight units
        units = {o["uuid"] for o in g.data["objects"] if o["kind"] == "unit" and o["player"] == self.foe and o.get("uuid")
                 and not herd.herdable(o["name"])}                     # AoE2: a sheep is captured, not attacked (#2049)
        for x in build.sides(g) if self.share else ():                 # also the units that the foe trained (#3107)
            if x.player == self.foe:
                units |= x.villagers.keys() | x.soldiers.keys()
        seen, T = g.seen_tiles(), g.map.T                              # the AoE2 AI sees only its sight (#2050)
        near = {k: p for k, p in g.positions(sorted(units)).items() if k not in inside
                and (int(p[0] // T), int(p[2] // T)) in seen}
        self.targets = {u: t for u, t in self.targets.items()          # a unit that comes in sight goes before a
                        if t not in g.forts or not any(self.reach(u, mine[u], p) and not self.gave_up(u, k, p)
                                                       for k, p in near.items())}   # building
        free = sorted(mine.keys() - self.targets.keys())
        forts, orders = None, {}
        for u in free:
            ok = {k: p for k, p in near.items() if self.reach(u, mine[u], p) and not self.gave_up(u, k, p)}
            if not ok:                                                 # no unit in reach, for example only a ship on
                if forts is None:                                      # the water: the buildings, as in AoE2 (#1770)
                    forts = {t: ((b[0] + b[3] + 1) / 2, b[1], (b[2] + b[5] + 1) / 2) for t, b in self.forts().items()}
                ok = {k: p for k, p in forts.items() if self.reach(u, mine[u], p) and not self.gave_up(u, k, p)}
            if not ok and self.lost.pop(u, None):                      # nothing else left: try the old targets again
                ok = {k: p for k, p in {**near, **forts}.items() if self.reach(u, mine[u], p)}
            if not ok:
                continue
            t = min(ok, key=lambda k: (math.dist(ok[k], mine[u]), k))
            self.targets[u] = t
            orders.setdefault(t, []).append(u)
        for t, us in sorted(orders.items()):
            if t in g.forts:
                g.sieged.add(t)                                        # Gather.fall frees its footprint
            ai.attack(g.game, us, [g.soldiers[u] for u in us], g.map.T, t,
                      [gather.NORMAL * train.speed(g, g.soldiers[u], u) for u in us])

    def stalled(self, mine):
        """Drop the target of each soldier that came no block nearer to it and did no damage to it for STALL AoE2
        seconds, and the unit target that went on the water out of its reach (#3441). In the games of #3324, 13 to 40
        soldiers destroyed nothing for 26 minutes: a soldier kept a live target that it could not hit (a garrisoned
        unit, #3429), and a unit in sight takes the soldiers away from a building. The soldier keeps the position of
        the target that it gave up (self.lost): it takes it again only after the target moved."""
        g = self.g
        pos = g.positions(sorted({t for t in self.targets.values() if t not in g.forts}))
        hps = {t: self.hp(t) for t in sorted(set(self.targets.values()))}   # one command for each target
        for u, t in sorted(self.targets.items()):
            if t in pos and not self.reach(u, mine[u], pos[t]):
                del self.targets[u]                                    # a ship that sailed away from the shore
                continue
            gap = box_gap(g.forts[t], mine[u]) if t in g.forts else math.dist(pos[t][::2], mine[u][::2]) if t in pos \
                else math.inf
            hp, last = hps[t], self.chase.get(u)
            if last is None or last[0] != t or gap < last[1] - 1 or hp is not None and last[2] is not None and hp < last[2]:
                self.chase[u] = (t, min(gap, last[1]) if last and last[0] == t else gap, hp, self.time)
            elif self.time - last[3] >= STALL:
                del self.targets[u]
                self.lost.setdefault(u, {})[t] = pos.get(t)
        self.chase = {u: c for u, c in self.chase.items() if self.targets.get(u) == c[0]}
        self.lost = {u: k for u, k in self.lost.items() if u in mine}

    def gave_up(self, u, t, p):
        """True when soldier u gave up target t (stalled) and t is still near the place where it gave up: a building
        does not move, a unit must move a tile away first."""
        if t not in self.lost.get(u, ()):
            return False
        was = self.lost[u][t]
        return was is None or math.dist(was[::2], p[::2]) < self.g.map.T

    def hp(self, t):
        """The hit points of target t (the score aoe_hp of a building, the Health of a unit), or None."""
        if t in self.g.forts:
            m = re.search(r" has (-?\d+) ", self.g.command(f"scoreboard players get {t} aoe_hp"))
        else:
            m = re.search(gather.NUMBER, self.g.command(f"data get entity {t} Health").rsplit(":", 1)[-1])
        return float(m[1]) if m else None

    def reach(self, u, at, to):
        """True when soldier u at `at` can attack a target at `to`. AoE2: a land unit cannot walk to a ship on the water
        (#1658): it attacks a target on a water cell only with its range, from the land. A ship attacks all."""
        wet = self.g.map.y(math.floor(to[0]), math.floor(to[2])) is None
        if not wet or self.g.map.y(math.floor(at[0]), math.floor(at[2])) is None:
            return True
        return math.dist(at[::2], to[::2]) <= combat.stats(self.g.soldiers[u]).range * self.g.map.T

    def forts(self):
        """{target UUID: box} of the buildings of the foe whose target entity lives: those of the map and those that
        the foe built in the game (build.target, #1819)."""
        g = self.g
        return {u: box for u, box in sorted(g.forts.items()) if g.fort_players.get(u) == self.foe
                and "passed" in g.command(f"execute if entity {u}")}

    def recruit(self):
        """Keep QUEUED units in the queue of each training building: villagers at the town centers up to
        self.villagers, and the first military unit of the age at the other buildings, when the resources are there.
        A town center comes first: the villagers get the resources first."""
        g = self.g
        for rect, name in sorted(train.homes(g).items(), key=lambda kv: (kv[1] != "TOWN_CENTER", kv[0])):
            more = len(g.villagers) + sum(e["name"] == "VILLAGER_MALE" for q in g.queues.values() for e in q)
            units = ["VILLAGER_MALE"] if name == "TOWN_CENTER" else \
                [n for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS and not build.locked(g, n)]
            for n in units[:1]:
                while len(g.queues.get(rect, [])) < QUEUED and (n != "VILLAGER_MALE" or more < self.villagers) \
                        and all(g.stock[r] >= v for r, v in train.price(g, n).items()) \
                        and train.queue(g, self.nobody, (rect[0], rect[2]), n):
                    more += n == "VILLAGER_MALE"

    def build(self):
        """Start the next house, farm or building of ORDER when the bot can pay for it and no site of it is unfinished.
        A farm when no food source is left at its base (#1026, #1810), at most one for each food villager of the shares."""
        g = self.g
        if open_ := [s for s in g.sites if not s.get("done")]:           # one site at a time
            for site in open_:                                         # its builder left or died (#1121)
                if g.villagers and not any(v.site is site and v.state != "idle" for v in g.villagers.values()):
                    self.builder(site)
            return
        cap, have = train.limit(g), train.owned(g)
        farms = sum(k > 0 for t, k in g.map.farms.items() if t in g.map.own_farms)
        hungry = not any(k > 0 for k in self.sources("food").values()) and farms < math.ceil(self.shares()["food"] * len(g.villagers))
        name = "HOUSE" if g.pop >= cap - HOUSE_GAP and cap < train.max_pop(g) else "FARM" if hungry else \
            next((n for n in self.order if (n not in have or self.remote(n)) and not build.locked(g, n)), None)
        if name is None or any(g.stock[r] < v for r, v in build.price(g, name).items()):
            return
        center = self.center()
        if (res := NEAR.get(name)) and (full := [t for t, k in self.sources(res).items() if k > 0]):
            T = g.map.T
            center = min(((t[0] * T + T // 2, t[1] * T + T // 2) for t in full), key=lambda c: (math.dist(c, center), c))
        if center is None or (rect := build.near(g, name, center)) is None or not g.villagers:
            return
        self.builder(build.found(g, name, rect))

    def remote(self, name):
        """True when name takes a resource (NEAR) whose sources with something left are all farther than FAR from an
        own drop site of it: then the bot builds one more camp there (#3402)."""
        g = self.g
        if not (res := NEAR.get(name)) or not (full := [t for t, k in self.sources(res).items() if k > 0]):
            return False
        T, drops = g.map.T, [c for d in g.map.drops.get(res, ()) for c in d]
        return all(math.dist(((t[0] + 0.5) * T, (t[1] + 0.5) * T), c) > FAR * T for t in full for c in drops)

    def builder(self, site):
        """Send one villager to build site: an idle one, else the nearest."""
        g = self.g
        x0, x1, z0, z1 = site["footprint"]
        x, z = (x0 + x1) / 2, (z0 + z1) / 2
        v = min(g.villagers.values(), key=lambda v: (v.state != "idle", math.dist(v.cell, (x, z)), v.uuid))
        g.build(site, {v.uuid})

    def center(self):
        """The middle block cell of the first own town center, or None."""
        tc = next((o["footprint"] for o in self.g.data["objects"] if o["kind"] == "building"
                   and o["player"] == self.g.player and o["name"] == "TOWN_CENTER"), None)
        return tc and ((tc[0] + tc[2]) // 2, (tc[1] + tc[3]) // 2)
