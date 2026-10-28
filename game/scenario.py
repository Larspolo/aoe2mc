"""
The scenario mode of the game program (#2540, epic #2538; run.py --mode scenario): each player starts with the start
resources and the population limit of the scenario (tab "Players" of the AoE2 DE scenario editor), not with the lobby
settings. The converter writes them into aoe2mc.json "players" ("resources", "pop_limit", #2539). A player without
them (a random map, a recorded game, an old scenario) keeps the lobby values.
Each person also gets a written book with the scenario texts (aoe2mc.json "messages": objectives, hints,
instructions ...), as the "Objectives" window of AoE2 DE, and the chat shows the instructions at the start (#2541).

A scenario trigger with the effect "Declare Victory" ends the game (#2542): its datapack function sets the score
#p<N> of aoe_win to 1 (aoe2mc.trigger_files), and victory() reads it with RCON once per conquest.EVERY seconds. Player N
and its allies see "Victory", the others "Defeat" (cheats.over). Minecraft feature: a scoreboard, no own logic in the
world.
A trigger with the effect "Change Diplomacy" sets the score #p<N>.p<M> of aoe_dip to the stance + 1 and #any to 1
(#2645): diplomacy() changes the stance of player N to player M in the players of aoe2mc.json and sends the plugin
commands of the alliances and neutral stances (gather.allies_command, gather.neutral_command).

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
import treaty  # noqa: E402

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
    not the bots (bot.Bot), once each EVERY seconds. gather.Gather.run calls it in the scenario mode."""
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
