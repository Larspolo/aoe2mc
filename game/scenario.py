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

    scenario.victory(g)    # gather.Gather.run, in the scenario mode
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

SLOT = "inventory.26"                                                  # the last slot of the inventory: not the hotbar
TAG = "aoe_book"                                                       # a person who has the book
EVERY = 1.0                                                            # seconds between two checks for new people


def book(who, messages):
    """The commands that put a written book with the scenario texts (aoe2mc.book_pages: one chapter per text, the
    title in bold) into the inventory slot SLOT of who: one command holds at most rcon.MAX bytes, so the pages after the
    first command go in with the item modifier set_written_book_pages (mode append). No command when all texts are
    empty."""
    out, pages = [], [page(p) for p in replay.aoe2mc.book_pages(messages)]
    head = (f"item replace entity {who} {SLOT} with written_book[written_book_content="
            '{title:"Objectives",author:"aoe2mc",pages:[', "]}]")
    more = (f'item modify entity {who} {SLOT} {{type:"minecraft:set_written_book_pages",mode:"append",pages:[', "]}")
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


def tick(g):
    """Give each person who joined since the last check the book, and show the instructions in the chat: the people,
    not the bots (bot.Bot), once each EVERY seconds. gather.Gather.run calls it in the scenario mode. Also the
    technologies of the triggers (research, #2577)."""
    research(g)
    if g.clock() < vars(g).get("book_at", 0.0):
        return
    g.book_at = g.clock() + EVERY
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
    for n in sorted(int(p) for p in g.players if int(p)):
        got = re.search(r" has (-?\d+) ", g.command(f"scoreboard players get #p{n} aoe_win") or "")
        if got and int(got[1]) > 0:
            return cheats.over(g, lambda m: gather.allied(g.players, n, m))   # allies win together


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
