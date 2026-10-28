"""Save a game of the game program and load it again (epic #2253, #2255).

The Minecraft save keeps the blocks and the mobs (their UUIDs too): the server plays the world in place and writes it
when it stops, so a save is a copy of the world folder. The state of the program (`gather.Gather`) goes into
`savegame.json` next to it: the resources, the technologies (the age comes from them) and the population of each player,
the train and research queues, the construction sites (also the done ones: the buildings of the game) and the rally
points (#2257), and the orders of the units (#2258): the job, target and load of each villager (also the rally walk and
the repair, #2380), the farmers, stances, control groups and garrisons. A villager keeps no path: after the load it walks
again with Minecraft path finding (P2).
The save also keeps the wonder and relic victory timers and the market prices (#2324), the time limit (#2356), the game
settings of the command line (`run.py` options, "settings"), the attack time and wave of the bot (#2325), the relics and the monk
orders (#2412: `monk.relics`, the conversions and the rest of the monks), the orders of the ships, the routes of the
trade carts and the state of the trebuchets (#2413), the passed time of the treaty (#2409), and the units inside the
transport ships and siege towers and the units on the way to them (#2411). The military units and villagers that the
player trained, and the new names of the upgrades, go into the save too (#2532): the world has their mobs, the Gather
counts them, gives them orders and upgrades them. The cheats that the player turned on go into the save too (#2533), and the
doctrines of the buildings, the targets of the attack orders and the fog toggle of "polo" (#2537).
"""
import json
import os
import shutil
import time

FILE = "savegame.json"
FIELDS = ("stock", "spare", "seconds", "repeats", "pop")              # dicts and numbers of Gather, as they are
PACKED = ("queues", "trained", "sites", "rally",                       # with tuples (a building rect, a cell): pack()
          "sieged",                                                    # the targets of attack orders: Gather.fall (#2537)
          "ruins",                                                     # the fallen start buildings: ruins.py (#3008)
          "soldiers", "units")                                         # the units of the game, trained or upgraded (#2532)
OPTIONAL = ("limit_left", "policy", "rates", "relic_timer", "switches", "upgraded", "wonder_shown", "wonders",   # only on a
            "wonders_gone")                                            # Gather that has them (#2324; the policy: #2515)
MONK = ("carrier_at", "converting", "faith", "fetching", "heal_time", "monk_at", "relic_gold", "relic_homes",
        "relic_time", "relics")                                        # game/monk.py: the relics and monk orders (#2412)
NOMAD = ("later", "nomad")                                             # a Nomad start: the first town center bonus (#2986)
ORDERS = ("patrols", "trigger_attributes", "trigger_costs",            # scenario.py: the patrols (#2647), attributes (#2763),
          "trigger_menus", "trigger_names",                            # costs (#2776), menu items (#2775), names (#2821)
          "trigger_places", "trigger_stacks", "trigger_times",         # the menu places (#2864), stacking (#2866), times (#2820),
          "trigger_trains", "trigger_civs")                            # train locations (#2865), civilization names (#2905)
ROUTES = ("trade", "trebs")                                            # trade.py, trebuchet.py: as OPTIONAL (#2413)
CHEATS = (                                                             # game/cheats.py: the cheats that the player
    "aegis",                                                           # turned on (#2533)
    "beyond",
    "free_techs",
    "pop_cap",
    "sharing",
)
COUNTERS = (                                                           # the parts that a tick did not use yet (#2514):
    "aura_time",                                                       # regen.py
    "cart_heal",                                                       # trade.py
    "garrison_heal",                                                   # garrison.py
    "herd_food",
    "hero_time",                                                       # regen.py: the heroes
    "military_time",                                                   # regen.py
    "regen_time",
    "repair_hp",                                                       # repair.py
    "repair_owed",
    "whole",                                                           # garrison.py: the units healed in full
)
LEFT = (                                                               # Gather: the resources left on the map (#2453)
    "crops",
    "dead",
    "trunks",
)
MAP = (                                                                # gather.Map: the amounts left (#2453), pack()
    "bushes",
    "carcasses",
    "farms",
    "fish",
    "herds",
    "mines",
    "rot",
    "traps",
    "trees",
)
VICTORY = (                                                            # the victory modes (#2476), pack()
    "conquest_seen",
    "corruption_at",
    "corruption_time",
    "defeated",
    "hill",
    "monument",
    "towns",
)
SCORE = (                                                              # Gather: the counts of score.py (#2475)
    "fallen",                                                          # spoils.py: the units that gave their spoils
    "given",                                                           # train.py: the free units and technologies
    "losses",
    "razed",
    "tributes",                                                        # diplomacy.py
)
SPOILS = (                                                             # spoils.py: the plugin scores that gave gold
    "attack_ticks",                                                    # (the world keeps the scores, #2513)
    "kills",
    "unit_kills",                                                      # the kills of enemy units for a policy (#2512)
)
TOGGLES = (                                                            # the choices of the player (#2537):
    "doctrines",                                                       # train.py: the doctrine of each building (#2483)
    "reveal",                                                          # fog.toggle: the cheat "polo" (#1390)
)
RIDERS = ("berths", "boarding", "cargo", "loading", "towers", "unloads")   # transport.py, siege_tower.py (#2411)
KEPT = (                                                               # the fields of Gather that only some have, pack():
    *CHEATS,
    *COUNTERS,
    *LEFT,                                                             # one tuple per line, in alphabetical order
    *MONK,                                                             # (parallel tickets add one, #2453)
    *NOMAD,
    *OPTIONAL,
    *ORDERS,
    *RIDERS,
    *ROUTES,
    *SCORE,
    *SPOILS,
    *TOGGLES,
    *VICTORY,
)
JOB = ("state", "load", "res", "job", "lap", "prey")                  # fields of a gather.Villager, as they are
BOT = ("time", "charged", "attack")                                    # fields of a bot.Bot, as they are (#2325)
SETTINGS = (                                                           # run.py options (#2325, #2409): one per line,
    "ai_difficulty",                                                   # in alphabetical order (parallel tickets add)
    "all_techs",
    "bot",
    "bot_attack",
    "cheats",
    "civ",
    "empire_wars",
    "end_age",
    "full_tech_tree",
    "handicap",
    "mode",
    "people",
    "pop_limit",
    "regicide",
    "resources",
    "reveal",
    "shared_exploration",
    "sudden_death",
    "teams",
    "treaty",
    "turbo",
    "unlock_speed",
    "unlock_teams",
    "victory",
    "victory_value",
)
NOT_SAVED = (                                                          # the fields that game/*.py sets on a Gather and the save
    # does not keep, one per line with its reason, in alphabetical order (tests/test_savegame_fields.py, #2535)
    "action_at",                                                       # scenario.py: the next check time
    "action_sent",                                                     # scenario.actions: a load sends them again
    "age_times",                                                       # recap.py: game times of this session (Gather.t0)
    "bar",                                                             # bossbar.py: the shown unit
    "book_at",                                                         # scenario.py: the next check time (the world keeps the tags)
    "bots",                                                            # run.play makes the bots again
    "capture",                                                         # herd.py: a tick timer
    "census",                                                          # train.py: a tick timer
    "chop",                                                            # bot.py: the setup value of the AI difficulty
    "conquest_at",                                                     # conquest.py: the next check time
    "data",                                                            # aoe2mc.json of the world
    "defend_at",                                                       # defend_wonder.py: the next check time
    "defender",                                                        # defend_wonder.setup makes it again
    "enemies",                                                         # the enemy units of aoe2mc.json: a dead one has no position
    "explore_at",                                                      # score.py: the next check time
    "fallen_at",                                                       # scenario.fallen: the next check time
    "fallen_sent",                                                     # scenario.fallen: a load sets the same score again
    "flares",                                                          # flare.py: the flares of a replay
    "fog",                                                             # fog.py: the next tick hides the units again; explored()
    "garrison_sent",                                                   # scenario.garrisons: a load sends them again
    "gate_refs",                                                       # scenario.py: a load forgets the plugin gates, so put them again (#2762)
    "ghosts",                                                          # build.py: the shown building to place
    "goto_idle",                                                       # goto.py: the next idle unit to show
    "haste_time",                                                      # train.haste: a tick timer
    "hasted",                                                          # train.haste: a load sends the values again
    "home",                                                            # bot.py: the town center of a bot
    "hurried",                                                         # regen.military: again in its next pass
    "kings",                                                           # regicide.setup makes it again
    "limit_at",                                                        # time_limit.py: the next check time
    "limit_shown",                                                     # time_limit.py: the shown text
    "noui",                                                            # the cheat "noui": only the hints
    "owners_at",                                                       # scenario.owners: the next check time
    "owners_sent",                                                     # scenario.owners: a load sets the same score again
    "peers",                                                           # run.py: the players of the game
    "player",                                                          # run.py: the player number
    "record",                                                          # record.py: run.play opens the file of --record again
    "regicide_at",                                                     # regicide.py: the next check time
    "repair_at",                                                       # repair.py: the place of a unit at its repair order, resume() sets it again
    "repairs",                                                         # orders(): the repair of each villager
    "research_at",                                                     # scenario.py: the next check time
    "research_skip",                                                   # scenario.py: the unknown technologies, found again
    "rows",                                                            # build.py: the shown building to place
    "ruins_at",                                                        # ruins.py: the next check time
    "ruins_seen",                                                      # ruins.py: the next answer of `aoe where` fills it again
    "scenario_at",                                                     # scenario.py: the next check time
    "score_at",                                                        # score.py: the next check time
    "shapes",                                                          # build.py: the shown building to place
    "share",                                                           # bot.py: the techs of the human player
    "spectator_at",                                                    # spectator.py: the next check time
    "spectator_sent",                                                  # spectator.tick: a load sends them again
    "spectator_views",                                                 # spectator.views: each spectator chooses again
    "speed",                                                           # run.py: the --speed option
    "sudden_death_at",                                                 # sudden_death.py: the next check time
    "tech_state_at",                                                   # scenario.py: the next check time
    "tech_state_sent",                                                 # scenario.tech_states: a load sends them again
    "trade_sent",                                                      # scenario.trading: a load sends them again
    "unlock_speed",                                                    # run.py: from the saved settings
    "unselectable",                                                    # scenario.selection: the world keeps the tags, the next check reads them
    "victory",                                                         # run.py: from the saved settings
    "victory_timer_at",                                                # scenario.py: the next check time
    "victory_timer_sent",                                              # scenario.victory_timers: a load sends them again
    "victory_value",                                                   # run.py: from the saved settings
    "wall_start",                                                      # build.py: the first corner of a wall
    "who",                                                             # the player name on the server
    "win_at",                                                          # scenario.py: the next check time
    "wonder",                                                          # defend_wonder.setup makes it again
    "wonder_at",                                                       # wonder.py: the next check time
)
SKIP = ("session.lock",)                                               # the lock of the running server


def sides(g):
    """The Gather of each player: the people (run.Side) and the bot (bot.Bot) keep theirs in .g."""
    return [g, *(s.g for s in getattr(g, "bots", ()) if hasattr(s, "g"))]


def pack(v):
    """v in a JSON form that unpack() turns back: a tuple and a dict with keys that are not text get a tag."""
    if isinstance(v, tuple):
        return {"tuple": [pack(x) for x in v]}
    if isinstance(v, (set, frozenset)):
        return {"set": sorted((pack(x) for x in v), key=repr)}
    if isinstance(v, dict) and not all(isinstance(k, str) for k in v):
        return {"items": sorted(([pack(k), pack(x)] for k, x in v.items()), key=repr)}
    if isinstance(v, dict):
        return {k: pack(x) for k, x in v.items()}
    return [pack(x) for x in v] if isinstance(v, list) else v


def unpack(v):
    if isinstance(v, dict) and set(v) == {"tuple"}:
        return tuple(unpack(x) for x in v["tuple"])
    if isinstance(v, dict) and set(v) == {"set"}:
        return {unpack(x) for x in v["set"]}
    if isinstance(v, dict) and set(v) == {"items"}:
        return {unpack(k): unpack(x) for k, x in v["items"]}
    if isinstance(v, dict):
        return {k: unpack(x) for k, x in v.items()}
    return [unpack(x) for x in v] if isinstance(v, list) else v


def dump(g):
    """The saved state of the game of g as a JSON dict (sorted keys and lists: the same game gives the same file).
    The settings of the game (run.main puts them on the server as .settings) go under "settings", the bot values under
    the player of the bot (#2325)."""
    d = {"players": {str(x.player): {**{f: getattr(x, f) for f in FIELDS}, "techs": sorted(x.techs),
                                     **{f: pack(getattr(x, f)) for f in PACKED}, **orders(x),
                                     **{f: pack(vars(x)[f]) for f in KEPT if f in vars(x)},
                                     "map": {f: pack(getattr(x.map, f)) for f in MAP},
                                     **({"explored": runs} if (runs := explored(x)) else {}),
                                     **({"known": sorted(map(list, k))} if (k := vars(x).get("fog", {}).get("known")) else {})}
                    for x in sides(g)}}
    for b in bots(g):
        d["players"][str(b.g.player)]["bot"] = {f: getattr(b, f) for f in BOT}
    if getattr(g.game, "settings", None):
        d["settings"] = dict(g.game.settings)
    if getattr(g.game, "treaty", 0):                                   # treaty.start: the time goes on (#2409)
        d["treaty_time"] = g.game.treaty_time
    d["stances"] = {n: {k: p[k] for k in ("team", "neutral", "sees") if k in p}   # the Diplomacy page (#2934), the
                    for n, p in sorted(g.players.items())}                       # triggers' stances and sight (#2989)
    return d


def explored(x):
    """The explored tiles of the minimap of the Gather x (fog.minimap, #2677) as sorted row runs [y, x0, x1] (both
    ends in the run): a large map has many tiles."""
    out = []
    for tx, ty in sorted(vars(x).get("fog", {}).get("explored", ()), key=lambda t: (t[1], t[0])):
        if out and out[-1][0] == ty and out[-1][2] == tx - 1:
            out[-1][2] = tx
        else:
            out.append([ty, tx, tx])
    return out


def bots(g):
    """The bots (bot.Bot) of g: Gather.bots also holds the Sides of the people."""
    return [b for b in getattr(g, "bots", ()) if hasattr(b, "charged")]


def orders(x):
    """The orders of the units of the Gather x (#2258): JSON has no tuple keys, so the tile and footprint keys go into
    sorted [key, value] lists."""
    repairs = vars(x).get("repairs", {})
    return {"villagers": {u: {**{f: getattr(v, f) for f in JOB}, "pos": list(v.pos), "tree": v.tree and list(v.tree),
                              "site": v.site and list(v.site["footprint"]), "goal": goal(v),
                              "repair": pack(repairs.get(u))} for u, v in sorted(x.villagers.items())},
            "farmers": sorted([list(t), u] for t, u in x.farmers.items()),
            "stances": dict(sorted(x.stances.items())),
            "groups": {str(n): sorted(us) for n, us in sorted(x.groups.items())},
            "garrisons": sorted([list(r), list(us)] for r, us in x.garrisons.items()),
            "ships": {u: {**{f: getattr(v, f) for f in JOB}, "pos": list(v.pos), "tree": v.tree and list(v.tree),
                          "site": v.site and list(v.site["footprint"]), "goal": v.path and list(v.path[-1]),
                          **({"route": pack(v.route)} if hasattr(v, "route") else {})}
                      for u, v in sorted(getattr(x, "ships", {}).items())}}


def sail_again(x, p):
    """Put the saved ship orders of p (orders) on the Gather x (#2413): a ship with a goal sails to it again on a new
    water path (fleet.sail_to); a warship chases its prey and a fishing ship fishes on in fleet.tick. Then the trade
    carts walk on with the leg of their route (trade.leg) and a walking trebuchet walks on to its target (Minecraft
    path finding, P2)."""
    import fleet
    import gather
    import trade
    import trebuchet
    for u, s in p.get("ships", {}).items():                           # a save from before #2413 has no ships
        v = x.ships.setdefault(u, gather.Villager(u, tuple(s["pos"])))
        for f in JOB:
            setattr(v, f, s[f])
        v.pos, v.tree, v.path = tuple(s["pos"]), s["tree"] and tuple(s["tree"]), []
        v.site = next((t for t in x.sites if list(t["footprint"]) == s["site"]), None)
        if "route" in s:
            v.route = unpack(s["route"])
        if s["goal"]:
            fleet.sail_to(x, v, v.state, {tuple(s["goal"])})
    for u, t in sorted(getattr(x, "trade", {}).items()):
        if t.get("legs"):
            trade.leg(x, u, t["legs"][0])
    for u, (st, _, then) in sorted(vars(x).get("trebs", {}).items()):
        if st == "walking":
            trebuchet.walk(x, u, *then)


def goal(v):
    """The cell of the rally walk of villager v (Paper: its goal, else the end of its path), else None (#2380)."""
    cell = v.goal or (v.path[-1] if v.path else None) if v.state == "to_rally" else None
    return cell and list(cell)


def give_orders(x, p):
    """Put the saved orders p (orders) on the Gather x. A villager that x does not know (trained in the game) comes
    back; a walking one walks again to its tree, drop site, construction site, rally point or repair (#2380)."""
    import gather
    import repair
    x.farmers = {tuple(t): u for t, u in p["farmers"]}
    x.stances, x.groups = dict(p["stances"]), {int(n): set(us) for n, us in p["groups"].items()}
    x.garrisons = {tuple(r): list(us) for r, us in p["garrisons"]}
    for u, s in p["villagers"].items():
        v = x.villagers.setdefault(u, gather.Villager(u, tuple(s["pos"])))
        for f in JOB:
            setattr(v, f, s[f])
        v.pos, v.tree, v.path = tuple(s["pos"]), s["tree"] and tuple(s["tree"]), []
        v.site = next((t for t in x.sites if list(t["footprint"]) == s["site"]), None)   # the sites of the save (#2257)
        key, cell = unpack(s.get("repair")), s.get("goal")             # a save before #2380 has neither
        if v.state in ("to_site", "build") and v.site is None or v.state == "to_rally" and not cell \
                or v.state in ("to_repair", "repair") and not repair.resume(x, u, key, v.state):
            v.state = "idle"
        elif v.state == "to_rally":
            x.go(v, "to_rally", {tuple(cell)})
        elif v.state == "to_site":
            x.build(v.site, {u})
        elif v.state == "to_tree":
            x.go(v, "to_tree", x.goals(v.tree))
        elif v.state == "to_drop":
            x.go(v, "to_drop", x.drop_goals(v))
        elif v.state == "to_prey":
            v.state = "hunt"                                           # the hunter follows its animal (Gather.strike)
    sail_again(x, p)


def board_again(x):
    """The units of the Gather x on the way to a transport ship or a siege tower walk to it again (#2411): the ship's
    shore cell, the tower's feet. Minecraft path finding (P2), as transport.order and siege_tower.order."""
    import ai
    import train
    walks = [(u, c[0] + 0.5, x.map.y(*c), c[1] + 0.5) for u, (_, c) in sorted(vars(x).get("loading", {}).items())]
    walks += [(u, *p) for u, t in sorted(vars(x).get("boarding", {}).items()) if (p := x.pos(t))]
    for u, *at in walks:
        name = "VILLAGER" if u in x.villagers else x.soldiers.get(u, "")
        ai.move(x, u, name, x.map.T, *at, ai.NORMAL * train.speed(x, name))


def load(g, d):
    """Put the saved state d (dump) on the Gather of each player that it names, and show the resources again."""
    import build
    import gather
    import train
    for x in sides(g):
        p = d["players"].get(str(x.player))
        if p is None:
            continue
        for f in FIELDS:
            setattr(x, f, type(getattr(x, f))(p[f]))
        x.techs = set(p["techs"])
        for f in PACKED + KEPT:                                        # the next tick shows the boss bars again
            if f in p:                                                 # a save before #2257 has no queues
                setattr(x, f, unpack(p[f]))
        for site in x.sites:                                           # the buildings work again: farms, drops, forts (#2980)
            build.settle(x, site, loaded=True)                         # before the saved amounts, which win
        for f, v in p.get("map", {}).items():                          # a save before #2453 has no map
            m = getattr(x.map, f)                                      # in place: the bot shares these (#2983)
            m.clear()
            m.update(unpack(v))
        for tile in [t for ts in x.map.mines.values() for t, n in ts.items() if n <= 0]:
            x.map.emptied(x.map.spot(tile))                            # empty at the save: as Gather.dig, berries
        for tile in [t for t, n in x.map.bushes.items() if n <= 0]:
            x.map.emptied(x.map.cells(tile))
        if "explored" in p:                                            # the minimap: the next fog.tick sends it all
            fog = vars(x).setdefault("fog", {"hidden": set(), "at": None})
            fog.pop("map", None)
            fog["explored"] = {(tx, ty) for ty, x0, x1 in p["explored"] for tx in range(x0, x1 + 1)}
        if "known" in p:                                               # the seen buildings: fog.know after the load (#3079)
            vars(x).setdefault("fog", {"hidden": set(), "at": None}).update(known={tuple(k) for k in p["known"]})
        if "villagers" in p:                                           # a save from before #2258 has no orders
            give_orders(x, p)
        board_again(x)
        x.show_stock()                                                 # the sidebar of the resources (Gather.setup)
        train.sidebar(x)
    for b in bots(g):                                                  # its attack time and wave go on (#2325)
        for f, v in d["players"].get(str(b.g.player), {}).get("bot", {}).items():
            setattr(b, f, v)
    for n, row in d.get("stances", {}).items():                        # diplomacy.change (#2934)
        p = g.players.setdefault(n, {})
        p.pop("team", None)
        p.pop("neutral", None)
        p.pop("sees", None)
        p.update(row)
    if "stances" in d:
        g.command(gather.allies_command(g.players))
        g.command(gather.neutral_command(g.players))


def settings(a, d, given=()):
    """Put the settings of the saved state d on the run.py options a, except the options in given (the player gave
    them with --load: they win). A save before #2325 has no settings: a keeps the options of the command line.
    A given --bot-attack also wins over the saved attack time of the bot."""
    for k, v in d.get("settings", {}).items():
        if k in SETTINGS and k not in given:
            setattr(a, k, v)
    if "teams" in given:                                             # the teams given here win over the stances
        d.pop("stances", None)
    if "bot_attack" in given:
        for p in d["players"].values():
            p.get("bot", {}).pop("attack", None)


def folder(world):
    """The folder of the saves of world: saves/ next to it."""
    return os.path.join(os.path.dirname(os.path.abspath(world)), "saves")


def save(g, player):
    """Save the running game (the button "Save" of the Game menu, #2259): the world after `save-all flush`, with no
    autosave while it copies, and the state of all players (the Gather of run.play, also for a click of another
    person). The chat line of player names the save. Returns its path."""
    game = g.game
    game.command("save-off")
    game.command("save-all flush")
    try:
        path = write(folder(game.world), game.world, dump(getattr(game, "g", None) or g))
    finally:
        game.command("save-on")
    g.command(f"tellraw {player} " + json.dumps({"text": f"Saved the game: {os.path.basename(path)}", "color": "green"}))
    return path


def write(saves, world, state):
    """Copy the world and the state (dump) into a new folder under saves. Returns its path. A save in the same
    second as another one gets the suffix -2, -3 and so on (#3046)."""
    name = f"{os.path.basename(os.path.normpath(world))}-{time.strftime('%Y%m%d-%H%M%S')}"
    path, n = os.path.join(saves, name), 1
    while True:
        try:
            os.makedirs(path)
            break
        except FileExistsError:
            n += 1
            path = os.path.join(saves, f"{name}-{n}")
    shutil.copytree(world, os.path.join(path, "world"), ignore=lambda d, names: [n for n in names if n in SKIP])
    with open(os.path.join(path, FILE), "w") as f:
        json.dump(state, f, indent=1, sort_keys=True)
    return path


def read(path):
    """The state (dump) of the save folder path."""
    with open(os.path.join(path, FILE)) as f:
        return json.load(f)
