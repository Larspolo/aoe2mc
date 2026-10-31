"""The AoE2 achievements in the game program (#5279, epic #5277): grant(g, n, key) gives the advancement
aoe2mc:<key> of data/achievements.jsonl (written by aoe2mc.advancement_files, #5278) to the Minecraft players of
player n. Minecraft shows the toast and the chat line (/advancement grant). A bot (share set) has no Minecraft player.
Events (the key "event" of a line): "win" or "win <CIV>" (cheats.over, each player with won(n)); "age <TECH>" with an
optional "before" in game seconds (recap.aged, train.research). "win all" needs the wins of earlier games: not here."""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import civs  # noqa: E402

PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "achievements.jsonl")
ROWS = [json.loads(x) for x in open(PATH, encoding="utf-8") if x.strip()]


def grant(g, n, key):
    """Grant aoe2mc:<key> to the team of player n, once per player and key, only for a key of ROWS."""
    done = vars(g).setdefault("achieved", set())
    if (n, key) in done or key not in {r["name"].lower() for r in ROWS}:
        return
    done.add((n, key))
    g.command(f"advancement grant @a[team=p{n}] only aoe2mc:{key}")


def event(g, h, name, seconds=None):
    """Grant each line whose event is `name` to the player of Gather h (not a bot)."""
    if getattr(h, "share", None) or not hasattr(g, "command"):    # a bot, or a test double with no server
        return
    for r in ROWS:
        if r.get("event") == name and (seconds is None or seconds < r.get("before", float("inf"))):
            grant(g, h.player, r["name"].lower())


def won(g, h):
    event(g, h, "win")
    if hasattr(h, "data") and (civ := civs.real(h, h.player)):
        event(g, h, f"win {civ}")


def aged(g, name, seconds):
    event(g, g, f"age {name}", seconds)
