"""
The scenario mode of the game program (#2540, epic #2538; run.py --mode scenario): each player starts with the start
resources and the population limit of the scenario (tab "Players" of the AoE2 DE scenario editor), not with the lobby
settings. The converter writes them into aoe2mc.json "players" ("resources", "pop_limit", #2539). A player without
them (a random map, a recorded game, an old scenario) keeps the lobby values. resources: the trigger effects "Tribute" and
"Modify Resource" change the stocks (#2576).
Each person also gets a written book with the scenario texts (aoe2mc.json "messages": objectives, hints,
instructions ...), as the "Objectives" window of AoE2 DE, and the chat shows the instructions at the start (#2541).
The trigger effect "Research Technology" (#2577) sets a score of the datapack; research() (in tick()) gives the
technology. The conditions "Object Visible" and "Object Not Visible" (#2756) test a score that visible() sets from the
sight of the player (the fog of the game program).

A scenario trigger with the effect "Declare Victory" ends the game (#2542): its datapack function sets the score
#p<N> of aoe_win to 1 (aoe2mc.trigger_files), and victory() reads it with RCON once per conquest.EVERY seconds. Player N
and its allies see "Victory", the others "Defeat" (cheats.over). Minecraft feature: a scoreboard, no own logic in the
world.
A trigger with the effect "Change Diplomacy" sets the score #p<N>.p<M> of aoe_dip to the stance + 1 and #any to 1
(#2645): diplomacy() changes the stance of player N to player M in the players of aoe2mc.json and sends the plugin
commands of the alliances and neutral stances (gather.allies_command, gather.neutral_command).

The conditions "Researching Technology" and "Technology State" (#2769) test the score #p<N>.<technology> of
aoe_techstate: tech_states() sets it to the AoE2 TechnologyState from the queues and g.techs of player N.

The condition "Difficulty Level" (#2704) tests the score #level of aoe_difficulty: setup() sets it to the AoE2 value
("aoe2" of game/data/difficulty.jsonl) of the setting "AI difficulty" (run.py --ai-difficulty).

A trigger with the effect "Task Object" (#2646) tags the units in its area and writes the target block into the storage
aoe2mc:tasks (aoe2mc.task_lines): tasks() walks the tagged units there with the path finding of the Paper plugin
(aoe moveto, a selector), then removes the tags and the key. Vanilla has no walk-to command. "Patrol" and
"Attack Move" (#2647) put their orders into the list of the storage aoe2mc:orders in the same way: orders().

    scenario.victory(g)    # gather.Gather.run, in the scenario mode
    scenario.tick(g)       # the book, the tasks, the orders
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fog  # noqa: E402
import garrison  # noqa: E402
import gather  # noqa: E402
import rcon  # noqa: E402
import replay  # noqa: E402
import train  # noqa: E402
import table  # noqa: E402
import treaty  # noqa: E402

SLOT = "inventory.26"                                                  # the last slot of the inventory: not the hotbar
TAG = "aoe_book"                                                       # a person who has the book
EVERY = 1.0                                                            # seconds between two checks for new people
ORDERS = "aoe2mc:orders"                                               # the data storage of the trigger orders (#2647)
ATTRIBUTES = "aoe2mc:attributes"                                       # the storage of "Modify Attribute" (#2763)
MENUS = "aoe2mc:menus"                                                 # the storage of "Enable/Disable" (#2775)
COSTS = "aoe2mc:costs"                                                 # the storage of "Change Object Cost" (#2776)
NAMES = "aoe2mc:names"                                                 # the storage of "Change Technology Name" (#2821)
NEAR = 3                                                               # blocks: a patrol turns back this near its point
LEVELS = {r["name"]: r["aoe2"] for r in table.load("difficulty.jsonl")}  # "AI difficulty" -> AoE2 DifficultyLevel


def book(who, messages):
    """The commands that put a written book with the scenario texts (aoe2mc.book_pages: one chapter per text, the
    title in bold) into the inventory slot SLOT of who: one command holds at most rcon.MAX bytes, so the pages after the
    first command go in with the item modifier set_written_book_pages (mode append). No command when all texts are
    empty."""
    return written(who, SLOT, "Objectives", replay.aoe2mc.book_pages(messages))


def written(who, slot, title, parts):
    """The commands that put a written book with title and the pages parts ((title or None, text), page) into slot of
    who, in commands of at most rcon.MAX bytes (book; the recap book of recap.py, #2660)."""
    out, pages = [], [page(p) for p in parts]
    head = (f"item replace entity {who} {slot} with written_book[written_book_content="
            f'{{title:{json.dumps(title)},author:"aoe2mc",pages:[', "]}]")
    more = (f'item modify entity {who} {slot} {{type:"minecraft:set_written_book_pages",mode:"append",pages:[', "]}")
    while pages:
        start, end = more if out else head
        n = 1
        while n < len(pages) and len(f"{start}{','.join(pages[:n + 1])}{end}".encode()) <= rcon.MAX:
            n += 1
        out.append(f"{start}{','.join(pages[:n])}{end}")
        pages = pages[n:]
    return out


def page(part):
    """One book page as an SNBT text component: (title or None, text)."""
    title, text = part
    body = f"{{text:{json.dumps(text)}}}"
    return f'{{text:"",extra:[{{text:{json.dumps(title + chr(10) * 2)},bold:true}},{body}]}}' if title else body


def unread(who):
    """The selector of the people of who that have no book yet (TAG)."""
    return f"{who[:-1]},tag=!{TAG}]" if who.endswith("]") else f"{who}[tag=!{TAG}]"


def tasks(g):
    """Walk the units of each "Task Object" of the storage aoe2mc:tasks to its block (one RCON read for all tasks),
    then remove its tag from the units and its key from the storage, so it walks them once."""
    got = g.command("data get storage aoe2mc:tasks") or ""
    for k, x, y, z in re.findall(r"\b(k\d+_\d+): \[(-?[\d.]+)d, (-?[\d.]+)d, (-?[\d.]+)d\]", got):
        sel = f"@e[tag=aoe_task{k[1:]}]"
        g.command(f"aoe moveto {sel} {x} {y} {z}")
        g.command(f"tag {sel} remove aoe_task{k[1:]}")
        g.command(f"data remove storage aoe2mc:tasks {k}")


def tick(g):
    """Give each person who joined since the last check the book, and show the instructions in the chat: the people,
    not the bots (bot.Bot), once each EVERY seconds; then the tasks of the triggers (tasks) and their orders (orders).
    gather.Gather.run calls it in the scenario mode. Also the technologies of the triggers (research, #2577)."""
    research(g)
    garrisons(g)
    tech_states(g)
    if g.clock() < vars(g).get("book_at", 0.0):
        return
    g.book_at = g.clock() + EVERY
    tasks(g)
    orders(g)
    menus(g)
    visible(g)
    attributes(g)
    costs(g)
    names(g)
    messages = g.data.get("messages", {})
    text = re.sub(r"<[^<>]*>", "", messages.get("instructions", "")).strip()   # AoE2 color tags (book_pages)
    for who in sorted({x.who for x in [g, *(s.g for s in g.bots if not hasattr(s, "charged"))]}):
        sel = unread(who)
        if "passed" not in g.command(f"execute if entity {sel}"):
            continue
        for cmd in book(sel, messages):
            g.command(cmd)
        if text:
            g.command(f"tellraw {sel} " + json.dumps({"text": text, "color": "gold"}))
        g.command(f"tag {sel} add {TAG}")


def gate(g, order, ref):
    """Lock or unlock (order) the converted gate with the reference ref (#2762): the first order puts the portcullis
    of the game program on it (build.portcullis: the iron bars and `aoe gate`), then the plugin locks it
    (`aoe gate lock X Z`: the bars stay down for all units) or unlocks it (an own or allied unit opens it again).
    A diagonal gate has no portcullis yet: no lock."""
    import build                                                       # build imports gather
    kind = lambda o: next((n for n in sorted(build.GATES, key=len, reverse=True) if n in o["name"]), None)
    o = next((o for o in g.data.get("objects", ()) if o.get("ref") == ref and kind(o) and o.get("footprint")), None)
    if o is None or o["footprint"][2] - o["footprint"][0] == o["footprint"][3] - o["footprint"][1]:
        return
    x0, z0, x1, z1 = o["footprint"]
    done = vars(g).setdefault("gate_refs", set())                      # the gates with a portcullis
    if ref not in done:
        done.add(ref)
        build.portcullis(g, {"name": kind(o), "player": o["player"], "footprint": [x0, x1, z0, z1]})
    g.command(f"aoe gate {order} {(x0 + x1) // 2} {(z0 + z1) // 2}")


def orders(g):
    """The "Patrol" and "Attack Move" orders of the triggers (aoe2mc.order_lines, #2647): read and empty the list of
    the data storage ORDERS, and walk the tagged units with the Paper plugin (`aoe moveto`, Minecraft path finding).
    An attack move gives them the aggressive stance (the plugin attacks the enemies on the way, as
    replay.Replay.attack_move) and removes the tag. A patrol (g.patrols: [tag, [tile, middle of the area], leg]) walks
    to the tile and back, again and again: it turns when one of its units is NEAR its point, and ends when no unit has
    the tag. A new patrol with the same tag (a looping trigger) replaces the old one. A "Change Object Stance" order
    (aoe2mc.stance_lines, #2705) sets the stance of the tagged units and removes the tag. A "Stop Object" order
    (aoe2mc.stop_lines, #2754) stops the tagged units (`aoe stop`), ends their patrols as a new order of a person does
    (gather.Gather.end_patrols, #2674) and removes the tag. An "Unload" order (#2773): unload(). A "Lock Gate" or
    "Unlock Gate" order (aoe2mc.gate_lines, #2762) locks or unlocks the gate of its reference: gate(). A "Place
    Foundation" order (aoe2mc.foundation_lines, #2825): foundation(). "Train Unit" and "Initiate Research"
    (aoe2mc.train_lines, #2772): queues()."""
    got = g.command(f"data get storage {ORDERS} list") or ""
    new = re.findall(r'"(patrol|attack_move|stance|stop) (aoe_order[\w.]+) ?(-?\d+(?: -?\d+)*)?"', got)
    unloads = re.findall(r'"unload (\d+) (\d+) ?(-?\d+ -?\d+ -?\d+)?"', got)
    gates = re.findall(r'"(lock|unlock) (\d+)"', got)
    found = re.findall(r'"found (\d+) (\w+) (\d+) (\d+)"', got)
    queued = re.findall(r'"(train|research) (\d+) (\w+) ?(\d+)?"', got)
    if new or unloads or gates or found or queued:
        g.command(f"data remove storage {ORDERS} list")
    queues(g, queued)
    for player, ref, where in unloads:
        unload(g, int(player), int(ref), where)
    for order, ref in gates:
        gate(g, order, int(ref))
    for player, name, x, y in found:
        foundation(g, int(player), name, (int(x), int(y)))
    patrols = vars(g).setdefault("patrols", [])
    for order, tag, where in new:
        p, sel = [int(v) for v in where.split()], f"@e[tag={tag}]"
        if order == "stance":                                          # "Change Object Stance" (#2705)
            import combat                                              # combat -> gather -> scenario
            g.command(f"aoe stance {sel} {combat.STANCES[p[0]]}")
            g.command(f"tag {sel} remove {tag}")
            continue
        if order == "stop":                                            # "Stop Object" (#2754)
            for q in patrols:
                g.command(f"tag {sel} remove {q[0]}")
            g.command(f"aoe stop {sel}")
            g.command(f"tag {sel} remove {tag}")
            continue
        if order == "attack_move":
            g.command(f"aoe stance {sel} aggressive")
            g.command(f"aoe moveto {sel} {p[0]} {p[1]} {p[2]}")
            g.command(f"tag {sel} remove {tag}")
            continue
        patrols[:] = [q for q in patrols if q[0] != tag] + [[tag, [p[:3], p[3:6]], 0]]
        g.command(f"aoe moveto {sel} {p[0]} {p[1]} {p[2]}")
    for q in list(patrols):
        tag, points, leg = q
        x, y, z = points[leg % 2]
        if "passed" in g.command(f"execute positioned {x} {y} {z} if entity @e[tag={tag},distance=..{NEAR}]"):
            q[2] = leg + 1
            g.command(f"aoe moveto @e[tag={tag}] {' '.join(map(str, points[q[2] % 2]))}")
        elif "passed" not in g.command(f"execute if entity @e[tag={tag}]"):
            patrols.remove(q)


def foundation(g, player, name, tile):
    """A "Place Foundation" order (aoe2mc.foundation_lines, #2825): the construction site of building name of the
    player (a person or a bot) with the tile in its middle, for free as in AoE2, when the place is free and flat as for
    a click of the player (build.free, shore, water, level). Its villagers build it as any site. A wall, a gate, a
    building that the game program cannot build or a blocked place: nothing."""
    import build                                                       # build imports gather
    if name not in build.MENU or name in build.WALLS + build.GATES:
        return
    ok = build.shore if name in build.SHORE else build.water if name in build.WATER else build.free
    for x in [g, *(s.g for s in g.bots)]:
        if x.player != player or "objects" not in x.data:
            continue
        T = x.map.T
        rect = build.area(x, name, (tile[0] * T + T // 2, tile[1] * T + T // 2))
        if ok(x, rect) and build.level(x, name, rect):
            build.found(x, name, rect, free=True)


def unload(g, player, ref, where):
    """An "Unload" order (aoe2mc.unload_lines, #2773): the units inside the building ref of the player (a person or a
    bot: garrison.holders) come out (garrison.out), and `aoe moveto` walks them to the block "x y z" when the order has
    one. A building that fell or that is not of the player: nothing."""
    for x in [g, *(s.g for s in g.bots)]:
        if x.player != player or "objects" not in x.data:
            continue
        rect = next((r for r, o in garrison.holders(x).items() if o.get("ref") == ref), None)
        for u in garrison.out(x, rect) if rect is not None else []:
            if where:
                x.command(f"aoe moveto {u} {where}")


def queues(g, queued):
    """The "train <ref> <unit> <quantity>" and "research <ref> <technology>" orders of the triggers (#2772): queue them
    at the converted building of that reference, for its player (the people and the bots), as clicks of its menu
    (train.queue): the player pays, and a full queue, a missing technology or too few resources stop the rest."""
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    refs = {o["ref"]: o for o in g.data.get("objects", ()) if o["kind"] == "building" and o.get("ref") is not None}
    for _, ref, name, n in queued:
        o = refs.get(int(ref))
        if o is None or (x := sides.get(o["player"])) is None:
            continue
        x0, z0, _, _ = o["footprint"]
        for _ in range(int(n or 1)):
            if not train.queue(x, getattr(x, "who", "@a"), (x0, z0), name):
                break


def costs(g):
    """The new costs of "Change Object Cost" (aoe2mc.cost_lines, #2776): read and empty the list of the data storage
    COSTS, and keep each cost in trigger_costs of the side of its player (the people and the bots): civs.cost uses it
    in place of the cost with the civilization bonuses, in the menus and when the player pays. A later line wins."""
    new = re.findall(r'"(\d+) (\w+)((?: [a-z]+=\d+)*)"', g.command(f"data get storage {COSTS} list") or "")
    if new:
        g.command(f"data remove storage {COSTS} list")
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    for player, name, cost in new:
        if int(player) in sides:
            vars(sides[int(player)]).setdefault("trigger_costs", {})[name] = \
                {r: int(v) for r, v in (part.split("=") for part in cost.split())}


def names(g):
    """The new names of "Change Technology Name" (aoe2mc.tech_name_lines, #2821): read and empty the list of the data
    storage NAMES, and keep each name in trigger_names of the side of its player (the people and the bots): the menus
    of that player show it (train.show). A later line wins. Minecraft prints a text with a double quote in single
    quotes."""
    got = g.command(f"data get storage {NAMES} list") or ""
    new = re.findall(r'"(\d+) (\w+) ((?:[^"\\]|\\.)*)"|\'(\d+) (\w+) ((?:[^\'\\]|\\.)*)\'', got)
    if new:
        g.command(f"data remove storage {NAMES} list")
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    for found in new:
        player, name, text = found[:3] if found[0] else found[3:]
        if int(player) in sides:
            vars(sides[int(player)]).setdefault("trigger_names", {})[name] = re.sub(r"\\(.)", r"\1", text)


def attributes(g):
    """The changes of "Modify Attribute" (aoe2mc.attribute_lines, #2763): read and empty the list of the data storage
    ATTRIBUTES, and add each change to trigger_attributes of the side of its player (the people and the bots; a
    unit type or a class "@<class>" of "Modify Attribute for Class", train.applies, #2859):
    train.stats applies them in order, so the units that the player trains later get the new values. The units of the
    type that exist get the new values at once (the same commands as a technology, train.research)."""
    import civs, combat                                                # combat -> gather -> scenario
    new = re.findall(r'"(\d+) (@?\w+) (\w+) ([1-5]) (-?[\d.]+)"', g.command(f"data get storage {ATTRIBUTES} list") or "")
    if new:
        g.command(f"data remove storage {ATTRIBUTES} list")
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    for player, name, field, op, q in new:
        if (x := sides.get(int(player))) is None or field not in combat.Stats._fields:
            continue
        vars(x).setdefault("trigger_attributes", []).append([name, field, int(op), float(q)])
        for uuid, n in [(u["uuid"], u["name"]) for u in x.units if "uuid" in u] + list(x.soldiers.items()):
            if not train.applies(name, n):                             # a type, or a class (#2859)
                continue
            s = train.stats(x, n)
            x.command(combat.stats_command(uuid, n, s, civs.taken(x, n), civs.friendly(x, n)))
            if field == "range" and (cmd := combat.range_command(uuid, n, x.map.T, s=s)):
                x.command(cmd)


def menus(g):
    """The items of "Enable/Disable Object" and "Enable/Disable Technology" (aoe2mc.menu_lines, #2775): read and empty
    the list of the data storage MENUS, and keep each item in trigger_menus of the side of its player (True: on). An
    item that is off is not in the menus (civs.missing); an item that is on is there also when the civilization does
    not have it or the age is not reached (train.unlocked): as in AoE2, the age technology only enables its items."""
    new = re.findall(r'"(\d+) (\w+) (on|off)"', g.command(f"data get storage {MENUS} list") or "")
    if new:
        g.command(f"data remove storage {MENUS} list")
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    for player, name, on in new:
        if int(player) in sides:
            vars(sides[int(player)]).setdefault("trigger_menus", {})[name] = on == "on"


def bot_seats(players, people):
    """[(player, foe)] of the bots of the scenario mode (#2543): one bot for each computer player of aoe2mc.json
    "players" after the seats of the people. Its foe is the first human player of the scenario that is not its ally
    (gather.allied), else player 1, as run.bot_seat. A human seat that no person takes stays idle, as in AoE2."""
    computer = sorted(int(p) for p, row in players.items() if row.get("computer") and int(p) > people)
    humans = sorted(int(p) for p, row in players.items() if not row.get("computer") and int(p) > 0)
    return [(b, next((p for p in humans if not gather.allied(players, b, p)), 1)) for b in computer]


def setup(g, mode="scenario"):
    """Put the scenario start values on the Gather of each player (the people and the bots) and show them. The victory
    setting of the scenario (aoe2mc.json "victory", #2566) replaces --victory: "custom" ends the game only by its
    triggers (no conquest, wonder or relic win, #2567)."""
    sides = [g, *(s.g for s in g.bots)]
    win = g.data.get("victory")
    for x in sides if win else ():
        x.victory = win["condition"]
        x.victory_value = win.get("years", win.get("score", getattr(x, "victory_value", None)))
    level = (getattr(g.game, "settings", None) or {}).get("ai_difficulty", "standard")
    g.command("scoreboard objectives add aoe_difficulty dummy")        # the condition "Difficulty Level" (#2704)
    g.command(f"scoreboard players set #level aoe_difficulty {LEVELS[level]}")
    g.command("scoreboard objectives add aoe_dipstate dummy")         # the condition "Diplomacy State" (#2757)
    states(g)
    rows = {x: g.players.get(str(x.player), {}) for x in sides}
    if not any("resources" in p or "pop_limit" in p for p in rows.values()):
        print("The world has no scenario start values: the game starts with the lobby settings.", file=sys.stderr)
        return g
    for x, p in rows.items():
        x.stock.update(p.get("resources", {}))
        x.pop_limit = p.get("pop_limit", x.pop_limit)
        for r in gather.RESOURCES:                                     # the sidebar of the resources (Gather.setup)
            x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
        train.sidebar(x)
    return g


def visible(g):
    """The conditions "Object Visible" and "Object Not Visible" of the triggers (#2756): set the score #r<ref>.p<player>
    of aoe_seen to 1 when a tile of the object is in the sight of the player (its own units and buildings, and those of
    its allies with "Shared Exploration": fog.shares), else 0, also for a dead unit or a player not in the game.
    aoe2mc.json "visible" lists the pairs (aoe2mc.visible_list). A converted world has no fog: the game program has it."""
    pairs = g.data.get("visible", ())
    if not pairs:
        return
    sides, T = fog.gathers(g), g.map.T
    objs = {o["ref"]: o for o in g.data["objects"] if o.get("ref") is not None}
    want = {u for h in sides for u in [*h.villagers, *h.soldiers]} | {o["uuid"] for o in objs.values() if "uuid" in o}
    pos = g.where(want)
    sight = {}
    for ref, player in pairs:
        if player not in sight:
            me = next((h for h in sides if h.player == player), None)
            sight[player] = set().union(*(h.seen_tiles(pos) for h in sides if fog.shares(me, h))) if me else set()
        o = objs.get(ref, {})
        if "footprint" in o:                                           # a building: [x0, z0, x1, z1) in blocks
            x0, z0, x1, z1 = o["footprint"]
            tiles = {(x, z) for x in range(x0 // T, (x1 - 1) // T + 1) for z in range(z0 // T, (z1 - 1) // T + 1)}
        elif "uuid" in o:                                              # a unit: where it is now, nothing when dead
            tiles = {(int(pos[o["uuid"]][0] // T), int(pos[o["uuid"]][2] // T))} if o["uuid"] in pos else set()
        else:
            tiles = {tuple(int(v) for v in o["tile"])} if "tile" in o else set()
        g.command(f"scoreboard players set #r{ref}.p{player} aoe_seen {int(bool(tiles & sight[player]))}")


def research(g):
    """Once per game second: give each technology of a fired "Research Technology" effect (aoe2mc.json "research",
    #2577) to its player at no cost, as the start age technologies (train.research), and reset its score. A loop
    trigger sets it again. A technology that the game program does not know: one line, then no more checks."""
    if g.clock() < vars(g).get("scenario_at", 0.0):
        return
    g.scenario_at = g.clock() + 1.0
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    skip = vars(g).setdefault("research_skip", set())
    for r in g.data.get("research", ()):
        if r["score"] in skip or not re.search(r" has [1-9]", g.command(f"scoreboard players get {r['score']} aoe_tech")):
            continue
        g.command(f"scoreboard players set {r['score']} aoe_tech 0")
        if r["technology"] not in train.TECHS or r["player"] not in sides:
            skip.add(r["score"])
            print(f"Research Technology: the game program has no {r['technology']} for player {r['player']}.",
                  file=sys.stderr)
            continue
        train.research(sides[r["player"]], {"name": r["technology"], "player": "@a"}, start=True)


def garrisons(g):
    """The score #g<ref> of aoe_gar of each converted building of a player (the people and the bots) that takes a
    garrison: the number of units inside (garrison.holders, g.garrisons), for the condition "Units Garrisoned" of the
    triggers (aoe2mc.trigger_files, #2714). One command per change: a unit goes in, all come out, the building falls."""
    sent = vars(g).setdefault("garrison_sent", {})
    for x in [g, *(s.g for s in g.bots)]:
        for rect, o in sorted(garrison.holders(x).items()) if "objects" in x.data else ():
            n = len(x.garrisons.get(rect, ()))
            if o.get("ref") is not None and sent.get(o["ref"], 0) != n:   # the objective starts with no score: 0
                g.command(f"scoreboard players set #g{o['ref']} aoe_gar {n}")
                sent[o["ref"]] = n


def tech_states(g):
    """Once per game second: the score #p<N>.<technology> of aoe_techstate of each pair of aoe2mc.json "tech_states"
    (the conditions "Researching Technology" and "Technology State", #2769) is the AoE2 TechnologyState of the
    technology for player N (tech_state). One command per change; a player with no Gather keeps no score."""
    if g.clock() < vars(g).get("tech_state_at", 0.0):
        return
    g.tech_state_at = g.clock() + 1.0
    sides = {x.player: x for x in [g, *(s.g for s in g.bots)]}
    sent = vars(g).setdefault("tech_state_sent", {})
    for n, name in g.data.get("tech_states", ()):
        if n in sides and name in train.TECHS and sent.get((n, name)) != (v := tech_state(sides[n], name)):
            g.command(f"scoreboard players set #p{n}.{name} aoe_techstate {v}")
            sent[(n, name)] = v


def tech_state(x, name):
    """The AoE2 TechnologyState of technology name for the Gather x: 3 researched, 2 researching (the head of a queue),
    4 queued, -1 disabled (the civilization does not have it), 1 ready (train.unlocked: its age and its technology
    before it), else 0."""
    if name in x.techs:
        return 3
    queues = [[e["name"] for e in q] for q in x.queues.values()]
    if any(q[:1] == [name] for q in queues):
        return 2
    if any(name in q for q in queues):
        return 4
    return -1 if train.civs.missing(x, name) else 1 if train.unlocked(x, name) else 0


def victory(g):
    """End the game when a trigger declared the victory of a player (the score #p<N> of aoe_win is 1)."""
    import cheats, conquest                                            # they import gather: import them late
    if g.ended or g.clock() < vars(g).get("win_at", 0.0):
        return
    g.win_at = g.clock() + conquest.EVERY
    diplomacy(g)
    visibility(g)
    for n in sorted(int(p) for p in g.players if int(p)):
        got = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #p{n} aoe_win") or "")
        if got and int(got[1]) > 0:
            return cheats.over(g, lambda m: gather.allied(g.players, n, m))   # allies win together


STANCES = {1: "ally", 2: "neutral", 4: "enemy"}                       # the score of aoe_dip: DiplomacyState + 1
SCORES = {kind: score for score, kind in STANCES.items()}


def stance(players, n, m, kind):
    """Set the stance of player n to player m ("ally", "neutral" or "enemy") in the players of aoe2mc.json. An alliance
    is a team (`team`, the groups of `aoe allies`): an ally joins the team of m, and a player that leaves an ally
    leaves its whole team, as the alliances of a world are groups."""
    row, other = players.setdefault(str(n), {}), players.setdefault(str(m), {})
    neutral = sorted(set(row.get("neutral", [])) - {m} | ({m} if kind == "neutral" else set()))
    row.pop("neutral", None)
    row |= {"neutral": neutral} if neutral else {}
    if (kind == "ally") == gather.allied(players, n, m):
        return
    if kind != "ally":
        row.pop("team")
        return
    if other.get("team") is None:
        other["team"] = 1 + max((p["team"] for p in players.values() if p.get("team") is not None), default=0)
    row["team"] = other["team"]


def mirror(players, n, m):
    """"Mirror Diplomacy" (#2822): player n takes the stance of player m toward each other player (m has no stance
    toward itself). The allies of m come last, so that n stays in their team: an alliance is a team (stance), so n is
    then an ally of m too. Else the stance between n and m stays."""
    kinds = {k: "ally" if gather.allied(players, m, k) else "neutral" if k in players[str(m)].get("neutral", ()) else
             "enemy" for k in sorted(int(p) for p in players if int(p)) if k not in (n, m)}
    for k in sorted(kinds, key=lambda k: kinds[k] == "ally"):
        stance(players, n, k, kinds[k])


def states(g):
    """Set the score #p<N>.p<M> of aoe_dipstate to the stance of player N to player M + 1 (STANCES): the condition
    "Diplomacy State" of the converted world tests it (#2757)."""
    ns = sorted(int(p) for p in g.players if int(p))
    for n, m in ((n, m) for n in ns for m in ns if n != m):
        kind = "ally" if gather.allied(g.players, n, m) else \
            "neutral" if m in g.players[str(n)].get("neutral", ()) else "enemy"
        g.command(f"scoreboard players set #p{n}.p{m} aoe_dipstate {SCORES[kind]}")


def diplomacy(g):
    """Apply the stances that "Change Diplomacy" triggers set (the scores of aoe_dip), then reset the scores. During a
    treaty (treaty.holds) all players stay neutral: the end of the treaty sends the new stances."""
    got = re.search(r" has (-?\d+) ", g.command("scoreboard players get #any aoe_dip") or "")
    if not got or int(got[1]) < 1:
        return
    g.command("scoreboard players reset #any aoe_dip")
    ns = sorted(int(p) for p in g.players if int(p))
    for n in ns:
        for m in ns:
            got = n != m and re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #p{n}.p{m} aoe_dip") or "")
            if got and int(got[1]) in STANCES:
                stance(g.players, n, m, STANCES[int(got[1])])
                g.command(f"scoreboard players reset #p{n}.p{m} aoe_dip")
    for n in ns:                                                       # "Mirror Diplomacy" (#2822), after the changes
        for m in ns:
            got = n != m and re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #m{n}.p{m} aoe_dip") or "")
            if got and int(got[1]) > 0:
                mirror(g.players, n, m)
                g.command(f"scoreboard players reset #m{n}.p{m} aoe_dip")
    states(g)
    g.command(gather.allies_command(g.players))
    if not treaty.holds(g):
        g.command(gather.neutral_command(g.players))


def visibility(g):
    """Apply "Set Player Visibility" (#2774, aoe2mc.visibility_lines): the score #p<N>.p<M> of aoe_vis is the state + 1.
    "Visible" puts M into the list "sees" of player N in the players of aoe2mc.json (fog.update then does not hide the
    units of M from N), "explored" and "invisible" take it out again. Then reset the scores."""
    got = re.search(r" has (-?\d+) ", g.command("scoreboard players get #any aoe_vis") or "")
    if not got or int(got[1]) < 1:
        return
    g.command("scoreboard players reset #any aoe_vis")
    ns = sorted(int(p) for p in g.players if int(p))
    for n in ns:
        for m in ns:
            got = n != m and re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #p{n}.p{m} aoe_vis") or "")
            if got and int(got[1]) in (1, 2, 3):
                row = g.players[str(n)]
                sees = set(row.get("sees", [])) - {m} | ({m} if int(got[1]) == 1 else set())
                row.pop("sees", None)
                row.update({"sees": sorted(sees)} if sees else {})
                g.command(f"scoreboard players reset #p{n}.p{m} aoe_vis")


def resources(g):
    """The trigger effects "Tribute" and "Modify Resource" of the converted world (#2576, aoe2mc.resource_lines): read
    the scores #p<N>.<resource> of aoe_set (a new value) and aoe_res (a change) with RCON once per EVERY seconds, put
    them into the stock of the Gather of player N, and reset them. A stock does not go below 0."""
    if g.clock() < vars(g).get("scenario_at", 0.0):
        return
    g.scenario_at = g.clock() + EVERY
    for x in [g, *(s.g for s in g.bots)]:
        for r in gather.RESOURCES:
            changed, name = False, f"#p{x.player}.{r.lower()}"
            for obj in ("aoe_set", "aoe_res"):
                if m := re.search(r" has (-?\d+) ", g.command(f"scoreboard players get {name} {obj}") or ""):
                    x.stock[r.lower()] = max(int(m[1]) + (x.stock[r.lower()] if obj == "aoe_res" else 0), 0)
                    g.command(f"scoreboard players reset {name} {obj}")
                    changed = True
            if changed:
                x.command(f"scoreboard players set {r} {x.board} {x.stock[r.lower()]}")
