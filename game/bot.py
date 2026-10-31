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
A resource whose stock is SPARE above the needs of the bot (the age reserve, the soldier, the economy technologies)
gets no share then (#4285). The bot spends on the next age first, then on technologies, then on units (spend).

Attack (#859): until the game time `attack` (AoE2 seconds) the soldiers stay at their buildings. Then each soldier
without a live target attacks the nearest unit of player `foe`, else its nearest building, with the mob AI of the
plugin (`ai.attack`, `aoe attack`). A soldier gets a new target when its target dies, and when it comes no nearer to
its target and does no damage to it for STALL seconds (#3441): AoE2 units that cannot reach a target take another one.

Difficulty (#2661, decision #2648): the AoE2 DE setting "AI difficulty" (run.py --ai-difficulty) is one line of
game/data/difficulty.jsonl (LEVELS): "gather" times the work rate of the bot villagers, "attack" times the time of the
first attack, "soldiers" in the first wave. AoE2 does not publish what each level changes: the values are a guess.

Defense (#3399): a predator in the sight of a bot villager gets the hunt order of the DEFENDERS nearest villagers, as
the AoE2 AI does. After the kill they go back to their last resource and source.
Town defense (#3954): an enemy unit in the sight of a bot building or villager gets the attack order of the bot soldiers
that are not in a wave, also before the attack time, as the AoE2 AI does. When it dies or leaves, they walk back.
"""
import json
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ai  # noqa: E402
import autoscout  # noqa: E402
import build  # noqa: E402
import combat  # noqa: E402
import conquest  # noqa: E402
import garrison  # noqa: E402
import gather  # noqa: E402
import herd  # noqa: E402
import per  # noqa: E402
import scout  # noqa: E402
import table  # noqa: E402
import train  # noqa: E402

SHARE = {"food": 0.4, "wood": 0.3, "gold": 0.2, "stone": 0.1}     # the villagers on each resource (a simple AoE2 bot)
WOOD = 0.2                                                         # the wood share for farms and houses with an army
SPARE = 200                                                        # stock above the needs: the resource gets no share
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
ANSWERS = {r["name"]: r["answer"] for r in table.load("taunts.jsonl") if "answer" in r}   # the taunts 42 to 44 (#4829)


def level_of(setting, k):
    """The level of bot k (0 first) of a setting: one name, or a comma list with one name for each bot in seat
    order; the last name serves the bots after the list (#4020)."""
    names = setting.split(",")
    return names[min(k, len(names) - 1)]


def box_gap(box, p):
    """Blocks from position p to the side of building box (x0, y0, z0, x1, y1, z1) on the ground; 0 inside it."""
    return math.hypot(max(box[0] - p[0], 0, p[0] - box[3] - 1), max(box[2] - p[2], 0, p[2] - box[5] - 1))


class Bot:
    order = ORDER                                                      # the buildings after the houses (build)

    def __init__(self, game, data, player=2, share=None, villagers=20, attack=ATTACK, foe=1, group=None,
                 difficulty="standard", own=None, script=None, **kw):
        """share: the Gather of the human player. Both then use the same trees, bushes and mines.
        villagers: the bot trains villagers up to this number, then soldiers.
        attack: the game time (AoE2 seconds) of the first attack on player foe, times the "attack" of the difficulty.
        group: the soldiers of the first wave (default: the "soldiers" of the difficulty); until then they stay at
        their buildings (#1051). difficulty: a name of LEVELS (#2661).
        own: the Gather of a person that the bot plays for (tools/play_check.py drives player 1, #3324): its run()
        steps it, so the bot only gives orders (orders()), and share is the Gather of the foe.
        script: the rules of an AoE2 AI script (per.parse, run.py --ai, #4529): they train, build and research in place
        of age_up(), research(), recruit() and the build order."""
        level = LEVELS[difficulty]
        self.g = own or gather.Gather(game, data, player=player, **kw)
        self.g.chop = {k: s / level["gather"] for k, s in self.g.chop.items()}   # seconds per unit: work_time
        self.villagers, self.attack, self.foe, self.share = villagers, attack * level["attack"], foe, share
        self.group = level["soldiers"] if group is None else group
        self.difficulty = difficulty                                   # the save keeps it (#4022)
        self.charged = False                                           # a wave attacks
        self.wave = set()                                              # its soldiers: new soldiers wait (#3953)
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
        self.giving, self.heard = {}, {}                               # ally -> "extra" or "all" (#4830); -> taunts read
        self.g.home = self.home                                        # the next bush or mine of Gather.nearest too
        self.guarded = -LOOK                                           # AoE2 seconds of the last look for predators
        self.defense = {}                                              # villager -> (predator, last res, last tree)
        self.guards = {}                                               # soldier -> (enemy in the town, its place before)
        self.g.work_on = False                                         # the bot gives the tasks after a build or a tree (#3271)
        self.scouted = False                                           # the start scouts get Auto Scout once (#3704)
        self.script = None if script is None else per.Script(script, self)
        self.said = {}                                                 # AoE2 player -> taunts it sent that the bot read (#4829)

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

    def answer(self):
        """Answer the taunts 42 to 44 of an allied person with one line to the team of the bot, as the AoE2 AI does
        (#4829). The taunts of each Gather since the last call (Gather.taunted) are read once."""
        g = self.g
        for x in {id(x): x for x in [*build.sides(g), g]}.values():
            log = getattr(x, "taunted", [])
            for n in log[self.said.get(x.player, 0):]:
                if n in ANSWERS and x.player != g.player and gather.allied(g.players, g.player, x.player):
                    text = ANSWERS[n].format(**self.facts())
                    g.command(f"tellraw @a[team=p{g.player}] " + json.dumps({"text": text, "color": "gray"}))
            self.said[x.player] = len(log)

    def facts(self):
        """The values of the answers: the age name, the attack time (AoE2 mm:ss) and the stock of the bot."""
        g = self.g
        m, s = divmod(int(self.attack), 60)
        return {"age": build.AGE_NAMES[build.ages(g)], "attack": f"{m}:{s:02d}",
                **{r: g.stock[r] for r in ("food", "wood", "gold", "stone")}}

    def orders(self):
        """Orders for the idle villagers, the sites, the queues and the soldiers."""
        g = self.g
        self.answer()
        if not self.scouted:                                           # the AoE2 AI scouts the map at the start (#3704)
            self.scouted = True
            scouts = {scout.CAVALRY, *scout.SCOUTS.values()}
            autoscout.start(g, [u for u, n in g.soldiers.items() if n in scouts])
        self.defend()
        self.guard()
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
        self.spend()
        self.time += g.tick * gather.NORMAL
        due = self.script.attacking if self.script else self.time >= self.attack   # a script: attack-now (#4530)
        if due and self.time >= self.looked + LOOK:   # each look costs RCON commands
            self.looked = self.time
            self.fight()

    def spend(self):
        """Spend the resources above keep(): the next age, then the technologies, then the units. The AoE2 AI
        researches its economy technologies before more soldiers: else each soldier takes the food above the reserve,
        and the bot never has the food of a technology (#4285: 2 technologies in 30 minutes).
        A script: one pass of its rules in each step (AoE2 checks them about 4 times each second, #4529)."""
        self.give()
        if self.script:
            self.script.step()
            return
        self.age_up()
        self.research()
        self.recruit()

    def give(self):
        """The tributes that the allies ask for with taunts (#4830, AoE2): 38 and 58 "extra" (the stock over reserve()),
        60 "all" (all stock), 59 stops. In lots, as the button of the diplomacy menu; no market: one chat line per ask."""
        import diplomacy
        import market
        g = self.g
        for x in build.sides(g):
            log = getattr(x, "taunted", [])
            new, self.heard[x.player] = log[self.heard.get(x.player, 0):], len(log)
            if x.player == g.player or diplomacy.stance(g, x.player) != "ally":
                continue
            for n in map(int, new):
                if n == 59:
                    self.giving.pop(x.player, None)
                elif n in (38, 58, 60):
                    if not market.markets(g):
                        g.command("tellraw @a " + json.dumps({"text": f"<Player {g.player}> I have no market: I cannot "
                                                                      "send tribute.", "color": "gray"}))
                        continue
                    self.giving[x.player] = "all" if n == 60 else "extra"
        for n, mode in sorted(self.giving.items()):
            keep = {} if mode == "all" else self.reserve()
            for r in diplomacy.RESOURCES:
                while g.stock[r] - keep.get(r, 0) >= diplomacy.cost(g, diplomacy.LOT) and market.markets(g) \
                        and diplomacy.send(g, self.nobody, n, r):
                    pass

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

    def guard(self):
        """Send the soldiers that are not in a wave against the enemy units in the sight of a bot building or villager
        (#3954): the AoE2 AI defends its town also before its attack. A soldier whose enemy died or left walks back to
        its place. Runs with defend(): one look each LOOK seconds."""
        g, T = self.g, self.g.map.T
        if self.time != self.guarded:                                  # defend() looked in this tick
            return
        if self.charged:                                               # a wave fights in fight(): its targets win
            self.guards = {}
            return
        eyes = [((x0 + x1 + 1) / 2, (z0 + z1 + 1) / 2, combat.sight(o["name"]) * T) for o in g.data["objects"]
                if o["kind"] == "building" and o["player"] == g.player and "footprint" in o
                for x0, z0, x1, z1 in [o["footprint"]]]
        eyes += [((x0 + x1 + 1) / 2, (z0 + z1 + 1) / 2, combat.sight(s["name"]) * T) for s in g.sites
                 if s.get("player", g.player) == g.player and s.get("done") for x0, x1, z0, z1 in [s["footprint"]]]
        eyes += [(v.pos[0], v.pos[2], combat.sight("VILLAGER_MALE") * T) for v in g.villagers.values() if v.pos]
        ally = lambda p: p != g.player and gather.allied(g.players, g.player, p)   # noqa: E731
        friends = [((x0 + x1 + 1) / 2, (z0 + z1 + 1) / 2, combat.sight(o["name"]) * T) for o in g.data["objects"]
                   if o["kind"] == "building" and ally(o["player"]) and "footprint" in o
                   for x0, z0, x1, z1 in [o["footprint"]]]
        friends += [((x0 + x1 + 1) / 2, (z0 + z1 + 1) / 2, combat.sight(s["name"]) * T) for x in build.sides(g)
                    for s in x.sites if ally(s.get("player", x.player)) and s.get("done")
                    for x0, x1, z0, z1 in [s["footprint"]]]       # the towns of the allies (#4021)
        units = sorted(u for u, n in g.enemies.items() if not herd.herdable(n))   # no allies (gather.allied, owners.add)
        seen = g.positions(units) if eyes or friends else {}
        near = {}
        for look in (eyes, friends):                                   # the own town first, then the allies
            near = near or {k: p for k, p in seen.items() if any(math.dist((x, z), (p[0], p[2])) <= r for x, z, r in look)}
        if not near and not self.guards:                               # each position costs one RCON command
            return
        mine = g.positions(sorted(u for u, n in g.soldiers.items() if combat.stats(n).attack))
        for u, (t, back) in sorted(self.guards.items()):
            if t not in near or u not in mine:
                del self.guards[u]
                if u in mine:
                    ai.move(g.game, u, g.soldiers[u], T, *back)
        if not near:
            return
        orders = {}
        for u in sorted(mine.keys() - self.guards.keys()):
            t = min(near, key=lambda k: (math.dist(near[k], mine[u]), k))
            self.guards[u] = (t, mine[u])
            orders.setdefault(t, []).append(u)
        for t, us in sorted(orders.items()):
            ai.attack(g.game, us, [g.soldiers[u] for u in us], T, t,
                      [gather.NORMAL * train.speed(g, g.soldiers[u], u) for u in us])

    def go(self, v, res):
        """Send villager v to the nearest source of res that has some left and a free cell next to it. False when there
        is none. An inner tree of a forest has no free cell (Gather.goals): the villager stopped at once, and each tick
        took the next inner tree, while move() gave it another order between (#3726: 67 s at the same place)."""
        g, T = self.g, self.g.map.T
        full = [t for t, k in self.sources(res).items() if k > 0 and self.time - self.failed.get(t, -RETRY) >= RETRY]
        near = sorted(full, key=lambda t: (math.dist(v.cell, ((t[0] + 0.5) * T, (t[1] + 0.5) * T)), t))
        if (tile := next((t for t in near if g.goals(t)), None)) is not None:
            g.send(tile, {v.uuid})
            self.sent[v.uuid] = tile
        return tile is not None

    def army(self):
        """The military unit that the first own training building (not a town center) trains, or None."""
        g = self.g
        return next((n for rect, name in sorted(train.homes(self.g).items()) if name != "TOWN_CENTER"
                     for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS
                     and not build.locked(g, n)), None)

    def shares(self):
        """SHARE, or the shares of the army (#1049) when the bot has its villager number and trains a soldier. With
        the army, a resource whose stock is SPARE above the needs of the bot (needs) gets no share, and the other
        shares grow: the AoE2 AI scripts change their gatherer percentages by the stock, else 4 villagers mine 1000
        gold that nothing takes while the economy technologies wait for wood (#4285)."""
        if self.script and (pct := self.script.percent()):            # the gatherer percentages of the script (#4530)
            return pct
        unit = len(self.g.villagers) >= self.villagers and self.army()
        if not unit:
            return SHARE
        cost = train.price(self.g, unit)
        total = sum(cost.values())
        share = {r: (WOOD if r == "wood" else 0) + (1 - WOOD) * cost.get(r, 0) / total for r in SHARE}
        need = self.needs(unit)
        rich = {r for r, v in share.items() if v and self.g.stock[r] >= need.get(r, 0) + SPARE}
        total = sum(v for r, v in share.items() if r not in rich)
        return {r: 0 if r in rich else v / total for r, v in share.items()} if rich and total else share

    def needs(self, unit):
        """{resource: amount} that the bot spends next: the reserve of keep(), the unit and the economy technologies
        of wanted()."""
        g, need = self.g, dict(self.keep())
        techs = [n for _, n in self.wanted() if train.value("economy", n)]
        for c in [train.price(g, unit), *(train.price(g, n) for n in techs)]:
            for r, v in c.items():
                need[r] = need.get(r, 0) + v
        return need

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
        (#2050), else to its nearest building. A wave starts with self.group soldiers; the soldiers that come later wait at home until they are a
        full wave too, as the AoE2 computer player does (#1051, #3953)."""
        g = self.g
        mine = g.positions(sorted(u for u, n in g.soldiers.items() if combat.stats(n).attack))   # a dead soldier
                                                                       # is not in it, a transport ship has no attack
        self.wave = getattr(self, "wave", set()) & mine.keys()           # the soldiers of the running wave
        group, most = self.group, 0
        if self.script:                                                # the attack group sizes of the script (#4530)
            group = self.script.number("sn-minimum-attack-group-size")
            most = self.script.number("sn-maximum-attack-group-size")
        if len(new := sorted(mine.keys() - self.wave)) >= group:       # the new soldiers wait for a full wave (#3953)
            self.wave |= set(new[:most] if most else new)
        self.charged = bool(self.wave)
        self.retarget()
        if not self.charged or self.foe is None:                      # no enemy: no attack (#3107)
            return
        mine = {u: p for u, p in mine.items() if u in self.wave}       # the others stay at their buildings
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

    def retarget(self):
        """When self.foe is out of the game (conquest.left), take the enemy still in the game (not an ally,
        gather.allied) whose town center is nearest to the own one, as the AoE2 AI (#4019); None with no enemy."""
        if self.share is None or self.foe is None or self.foe in (left := conquest.left(self.share)):
            return
        g, me = self.g, self.center()

        def far(p):
            tc = next((o["footprint"] for o in g.data["objects"] if o["kind"] == "building" and o["player"] == p
                       and o["name"] == "TOWN_CENTER"), None)
            return math.inf if tc is None or me is None else math.dist(me, ((tc[0] + tc[2]) / 2, (tc[1] + tc[3]) / 2))
        self.foe = min((p for p in sorted(left) if not gather.allied(g.players, g.player, p)), key=far, default=None)
        self.sides = (None, {})                                        # a new foe: decide each tile again

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
        A town center comes first: the villagers get the resources first. Soldiers keep reserve(): else each soldier
        takes the gold above keep(), and the bot never has the cost of its next technology (#4495)."""
        g, keep, army = self.g, self.keep(), self.reserve()
        for rect, name in sorted(train.homes(g).items(), key=lambda kv: (kv[1] != "TOWN_CENTER", kv[0])):
            more = len(g.villagers) + sum(e["name"] == "VILLAGER_MALE" for q in g.queues.values() for e in q)
            units = ["VILLAGER_MALE"] if name == "TOWN_CENTER" else self.soldiers(name)
            hold = keep if name == "TOWN_CENTER" else army
            for n in units[:1]:
                while len(g.queues.get(rect, [])) < QUEUED and (n != "VILLAGER_MALE" or more < self.villagers) \
                        and all(g.stock[r] >= v + hold.get(r, 0) for r, v in train.price(g, n).items()) \
                        and train.queue(g, self.nobody, (rect[0], rect[2]), n):
                    more += n == "VILLAGER_MALE"

    def reserve(self):
        """keep() and the cost of the first technology of wanted() whose building has a free queue: the AoE2 AI saves
        for its next technology before it trains more soldiers (#4495)."""
        g, need = self.g, dict(self.keep())
        busy = {rect for rect, q in g.queues.items() if any(e["name"] in train.TECHS for e in q)}
        n = next((n for rect, n in self.wanted() if rect not in busy), None)
        for r, v in (train.price(g, n) if n else {}).items():
            need[r] = need.get(r, 0) + v
        return need

    def soldiers(self, name):
        """The military units that building name trains now (recruit trains the first one)."""
        g = self.g
        return [n for n in train.trains(g, name) if gather.military(n) and n not in train.TECHS and not build.locked(g, n)]

    def wanted(self):
        """[(rect, technology)] that research takes when it has the cost: the economy technologies of the age at each
        building that offers them (the AoE2 AI does, #3949), the upgrade of the unit that the building trains (#3952:
        Militia to Man-at-Arms), so that recruit then trains the new unit, and the Blacksmith technologies that change a
        live or queued soldier of the bot (#3951). The economy technologies of all buildings come first (#4206).
        None while the bot has less than self.villagers villagers, and none at a building with a technology in its queue."""
        g = self.g
        if len(g.villagers) + sum(e["name"] == "VILLAGER_MALE" for q in g.queues.values() for e in q) < self.villagers:
            return []
        army = {n for n in [*g.soldiers.values(), *(e["name"] for q in g.queues.values() for e in q)]
                if n not in train.TECHS and gather.military(n)}

        def smith(n):                                                  # the technology changes a soldier of the bot
            return train.BUILDING_OF.get(n) == "BLACKSMITH" and any(
                train.TECHS[n](u, combat.stats(u)) != combat.stats(u) for u in sorted(army))
        wants = []                                                     # (rect, technology) in building order
        for rect, name in sorted(train.homes(g).items(), key=lambda kv: kv[0]):
            if any(e["name"] in train.TECHS for e in g.queues.get(rect, [])):
                continue
            line = set(self.soldiers(name)[:1])
            wants += [(rect, n) for n in train.trains(g, name) if n in train.TECHS and not build.locked(g, n) and (
                train.value("economy", n) or smith(n) or n in train.UPGRADES and line & {old for old, _ in train.lines(n, g)})]
        return sorted(wants, key=lambda w: not train.value("economy", w[1]))

    def research(self):
        """Research the technologies of wanted() in its order, one in each queue, with the resources above keep()."""
        g, keep, busy = self.g, self.keep(), set()
        for rect, n in self.wanted():
            if rect not in busy and all(g.stock[r] >= v + keep.get(r, 0) for r, v in train.price(g, n).items()) \
                    and train.queue(g, self.nobody, (rect[0], rect[2]), n):
                busy.add(rect)

    def next_age(self):
        """(age, missing): the next age (build.AGE_TECHS) when the bot has its villager number and the age is not
        queued, and the first building of its order that the present age allows and the bot lacks (None when it has
        each). (None, None) else. build.locked keeps an age above end_age out."""
        g = self.g
        if build.ages(g) >= len(build.AGE_TECHS) or len(g.villagers) < self.villagers:
            return None, None
        age, have = build.AGE_TECHS[build.ages(g)], train.owned(g)
        if train.queued(g, age) or build.locked(g, age):
            return None, None
        return age, next((n for n in self.order if n not in have and not build.locked(g, n)), None)

    def keep(self):
        """The resources that the bot keeps for its next age (#4087): the cost of the missing building of its order,
        then the cost of the age. Soldiers and technologies take only the resources above it, else they spend each
        60 food and 25 wood, and the bot never gets the 500 food of the Feudal Age or the wood of a Blacksmith."""
        g = self.g
        age, missing = self.next_age()
        if missing:
            return build.price(g, missing)
        tc = next((name for name in train.homes(g).values() if name == "TOWN_CENTER"), None)
        return train.price(g, age, tc) if age and tc else {}

    def age_up(self):
        """Queue the next age (next_age) at a town center when the bot has the cost of the age, as an AoE2 bot (#3912)."""
        g = self.g
        age, missing = self.next_age()
        if age is None or missing:
            return
        for rect, name in sorted(train.homes(g).items()):
            if name == "TOWN_CENTER" and age in train.trains(g, name) \
                    and all(g.stock[r] >= v for r, v in train.price(g, age, name).items()):
                train.queue(g, self.nobody, (rect[0], rect[2]), age)
                return

    def build(self):
        """Start the next house, farm or building of ORDER when the bot can pay for it and no site of it is unfinished.
        A farm when no food source is left at its base (#1026, #1810), at most one for each food villager of the shares.
        A bot with a script only finds builders for its open sites."""
        g = self.g
        if open_ := [s for s in g.sites if not s.get("done")]:           # one site at a time
            for site in open_:                                         # its builder left or died (#1121)
                if g.villagers and not any(v.site is site and v.state != "idle" for v in g.villagers.values()):
                    self.builder(site)
            return
        if self.script:                                                # the script builds (per.Script.act, #4529)
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
