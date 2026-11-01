"""
The command /controls (#5501, P8 of steering/project/PRINCIPLES.md): the controls of the game in the chat of the player
who types it, so that the play test needs no docs/PLAYTEST.md (section 4) in a browser. The vanilla trigger
`/trigger aoe_controls` does the job for a player who is no operator; the Paper plugin only adds the short name
`/controls` (AoePlugin.java), which sets the same score. gather.Gather.clicks calls tick().
"""
import json
import re

import lang

OBJECTIVE = "aoe_controls"


def keys():
    """The text keys of the lines, in the order of texts.jsonl (the head first)."""
    return [k for k in lang.en_us() if k.startswith("aoe2mc.controls.")]


def setup(g):
    g.command(f"scoreboard objectives add {OBJECTIVE} trigger")


def tick(g):
    """Enable the trigger, send the lines to each player that used it, and reset its score."""
    who = getattr(g, "who", "@a")
    g.command(f"scoreboard players enable {who} {OBJECTIVE}")
    sel = who[:-1] + f",scores={{{OBJECTIVE}=1..}}]" if who.endswith("]") else who + f"[scores={{{OBJECTIVE}=1..}}]"
    if "passed" not in g.command(f"execute if entity {sel}"):
        return
    for name in g.people():
        if name and re.search(r" has [1-9]", g.command(f"scoreboard players get {name} {OBJECTIVE}")):
            g.command(f"scoreboard players set {name} {OBJECTIVE} 0")
            for k in keys():
                g.command(f"tellraw {name} " + json.dumps(lang.text(k, color="gold" if k.endswith(".head") else "white")))
