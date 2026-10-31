"""The tutorial (#5161, epic #5160): run.py --play --tutorial. game/data/tutorial.jsonl has the steps in order: the
`name`, the `text` that the player reads, and the key "check" ("module.function", (g, row) -> True when the step is
done), as the goals of challenge.py. A new step is one data line and one check function.
Minecraft feature: a boss bar shows the step (the chat too), a title and a sound show a done step.

    tutorial.tick(g)   # gather.Gather.run, when g.tutorial is set
"""
import importlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import table  # noqa: E402

STEPS = table.load("tutorial.jsonl")
BAR = "aoe2mc:tutorial"


def selected(g, row):
    """Step "select": a villager of the player is in the selection (the selection of play:control)."""
    return bool(set(g.selected) & set(g.villagers))


def wood(g, row):
    """Step "wood": the stock has the wood of the key "need"."""
    return g.stock["wood"] >= row["need"]


def house(g, row):
    """Step "house": the player has a complete house (train.owned: no construction site)."""
    import train  # train imports gather, gather imports this module
    return "HOUSE" in train.owned(g)


def villager(g, row):
    """Step "villager": a villager is in the queue of a town center of the player (play:train)."""
    import train  # train imports gather, gather imports this module
    homes = train.homes(g)
    return any(homes.get(rect) == "TOWN_CENTER" and any(u["name"].startswith("VILLAGER") for u in q)
               for rect, q in g.queues.items())


def camps(g, row):
    """Step "camps": the player has each complete building of the key "buildings"."""
    import train
    return set(row["buildings"]) <= set(train.owned(g))


def food(g, row):
    """Step "food": the stock has the food of the key "need"."""
    return g.stock["food"] >= row["need"]


def feudal(g, row):
    """Step "feudal": the player is in the Feudal Age or later (play:ages)."""
    import build
    return build.ages(g) >= 1


def militia(g, row):
    """Step "militia": the player has the Militia of the key "count" (g.soldiers: the living military units)."""
    return sum(n == "MILITIA" for n in g.soldiers.values()) >= row["count"]


def camp(g, row):
    """Setup of step "camp": the complete buildings of the key "camp" ({AoE2 name: count}) of player 2 near the middle
    of the map, as challenge.besiege. Buildings do not attack. g.tutorial_camp: their target entities."""
    import build  # build imports gather, gather imports this module
    import combat
    middle, own = (g.map.n // 2, g.map.n // 2), g.player
    g.tutorial_camp = []
    for name, count in sorted(row["camp"].items()):
        for _ in range(count):
            if (rect := build.near(g, name, middle, reach=24)) is None:
                continue
            g.player = 2                                            # the site, its color and design of player 2
            try:
                site = build.found(g, name, rect, free=True)
            finally:
                g.player = own
            build.rise(g, site, float("inf"))
            x0, x1, z0, z1 = rect
            g.tutorial_camp.append(combat.target_uuid([x0, z0, x1, z1]))


def destroyed(g, row):
    """Step "camp": no building of the camp stands (Gather.free removes a fallen one from g.forts)."""
    return not set(vars(g).get("tutorial_camp", ())) & g.forts.keys()


def give(g, row):
    """Setup of a step: the resources of the key "give" go to the stock, so the step does not wait for a slow player.
    The board (the sidebar) gets them too: each payment removes from both (#3111), else the sidebar goes below 0 (#5332)."""
    for k, n in row["give"].items():
        g.stock[k] += n
        g.command(f"scoreboard players add {k.capitalize()} {g.board} {n}")


def known():
    """The names of the controls that a step can name in "controls" (#5164): the command stick and the selection wand
    (gather.py) and the items of the build menu (build.MENU)."""
    import build  # gather imports this module
    import gather
    return {"carrot_on_a_stick", gather.WAND, *build.MENU}


def unknown(row):
    """The names of the key "controls" of step row that the game program does not have."""
    return sorted(set(row["controls"]) - known())


def done(g, row):
    """True when step row is done (its "check" function)."""
    module, _, function = row["check"].rpartition(".")
    return getattr(importlib.import_module(module), function)(g, row)


def show(g, n):
    """The boss bar and the chat line of step n."""
    row = STEPS[n]
    if "setup" in row:                                                 # as the key "setup" of challenges.jsonl
        module, _, function = row["setup"].rpartition(".")
        getattr(importlib.import_module(module), function)(g, row)
    if n == 0:
        for cmd in (f'bossbar add {BAR} ""', f"bossbar set {BAR} color green", f"bossbar set {BAR} max {len(STEPS)}",
                    f"bossbar set {BAR} players @a"):
            g.command(cmd)
    g.command(f"bossbar set {BAR} name " + json.dumps(f"Step {n + 1}/{len(STEPS)}: {row['text']}"))
    g.command(f"bossbar set {BAR} value {n}")
    g.command("tellraw @a " + json.dumps({"text": row["text"], "color": "green"}))


def tick(g):
    """Show the first step; when the step is done, show a title and the next step. After the last step the chat says
    that the tutorial is complete, a title shows it and the game ends with the recap (cheats.over). g.tutorial_step: the index of the step, None before the start."""
    n = vars(g).get("tutorial_step")
    if n is None:
        g.tutorial_step = n = 0
        show(g, n)
    if n >= len(STEPS) or not done(g, STEPS[n]):
        return
    g.command("title @a subtitle " + json.dumps({"text": "Step done", "color": "green"}))
    g.command("title @a title " + json.dumps({"text": ""}))
    g.command("execute as @a at @s run playsound minecraft:entity.player.levelup master @s")
    g.tutorial_step = n = n + 1
    if n < len(STEPS):
        return show(g, n)
    import cheats  # cheats imports gather, gather imports this module
    g.command(f"bossbar remove {BAR}")
    g.command("tellraw @a " + json.dumps({"text": "The tutorial is complete.", "color": "green"}))
    g.command(f"title @a[team=p{g.player}] subtitle " + json.dumps({"text": "Tutorial complete", "color": "yellow"}))
    cheats.over(g, lambda p: p == g.player)                            # the end and the recap, as challenge.tick
