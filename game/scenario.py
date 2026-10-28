"""
The scenario mode of the game program (#2540, epic #2538; run.py --mode scenario): each player starts with the start
resources and the population limit of the scenario (tab "Players" of the AoE2 DE scenario editor), not with the lobby
settings. The converter writes them into aoe2mc.json "players" ("resources", "pop_limit", #2539). A player without
them (a random map, a recorded game, an old scenario) keeps the lobby values. resources: the trigger effects "Tribute" and
"Modify Resource" change the stocks (#2576).
Each person also gets a written book with the scenario texts (aoe2mc.json "messages": objectives, hints,
instructions ...), as the "Objectives" window of AoE2 DE, and the chat shows the instructions at the start (#2541).
The trigger effect "Research Technology" (#2577) sets a score of the datapack; research() (in tick()) gives the
technology.

A scenario trigger with the effect "Declare Victory" ends the game (#2542): its datapack function sets the score
#p<N> of aoe_win to 1 (aoe2mc.trigger_files), and victory() reads it with RCON once per conquest.EVERY seconds. Player N
and its allies see "Victory", the others "Defeat" (cheats.over). Minecraft feature: a scoreboard, no own logic in the
world.
A trigger with the effect "Change Diplomacy" sets the score #p<N>.p<M> of aoe_dip to the stance + 1 and #any to 1
(#2645): diplomacy() changes the stance of player N to player M in the players of aoe2mc.json and sends the plugin
commands of the alliances and neutral stances (gather.allies_command, gather.neutral_command).

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
    if g.clock() < vars(g).get("book_at", 0.0):
        return
    g.book_at = g.clock() + EVERY
    tasks(g)
    orders(g)
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


def orders(g):
    """The "Patrol" and "Attack Move" orders of the triggers (aoe2mc.order_lines, #2647): read and empty the list of
    the data storage ORDERS, and walk the tagged units with the Paper plugin (`aoe moveto`, Minecraft path finding).
    An attack move gives them the aggressive stance (the plugin attacks the enemies on the way, as
    replay.Replay.attack_move) and removes the tag. A patrol (g.patrols: [tag, [tile, middle of the area], leg]) walks
    to the tile and back, again and again: it turns when one of its units is NEAR its point, and ends when no unit has
    the tag. A new patrol with the same tag (a looping trigger) replaces the old one. A "Change Object Stance" order
    (aoe2mc.stance_lines, #2705) sets the stance of the tagged units and removes the tag. A "Stop Object" order
    (aoe2mc.stop_lines, #2754) stops the tagged units (`aoe stop`), ends their patrols as a new order of a person does
    (gather.Gather.end_patrols, #2674) and removes the tag."""
    new = re.findall(r'"(patrol|attack_move|stance|stop) (aoe_order[\w.]+) ?(-?\d+(?: -?\d+)*)?"',
                     g.command(f"data get storage {ORDERS} list") or "")
    if new:
        g.command(f"data remove storage {ORDERS} list")
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


def victory(g):
    """End the game when a trigger declared the victory of a player (the score #p<N> of aoe_win is 1)."""
    import cheats, conquest                                            # they import gather: import them late
    if g.ended or g.clock() < vars(g).get("win_at", 0.0):
        return
    g.win_at = g.clock() + conquest.EVERY
    diplomacy(g)
    for n in sorted(int(p) for p in g.players if int(p)):
        got = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #p{n} aoe_win") or "")
        if got and int(got[1]) > 0:
            return cheats.over(g, lambda m: gather.allied(g.players, n, m))   # allies win together


STANCES = {1: "ally", 2: "neutral", 4: "enemy"}                       # the score of aoe_dip: DiplomacyState + 1


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
    g.command(gather.allies_command(g.players))
    if not treaty.holds(g):
        g.command(gather.neutral_command(g.players))


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
