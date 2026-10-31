"""Texts as Minecraft `translate` components (#5344): a lang file of a resource pack can give a key in another
language; with no pack the client shows the English `fallback` of game/data/texts.jsonl."""
import json

import table

EN_US = {r["name"]: r["en_us"] for r in table.load("texts.jsonl")}


def text(key, *args, **style):
    """The text component of key ("aoe2mc.<key>") with the arguments args (one per %s) and the style (color, ...)."""
    if key not in EN_US:
        raise KeyError(f"no text {key} in game/data/texts.jsonl")
    if EN_US[key].count("%s") != len(args):
        raise ValueError(f"text {key}: {EN_US[key].count('%s')} arguments, not {len(args)}")
    out = {"translate": key, "fallback": EN_US[key]}
    if args:
        out["with"] = [a if isinstance(a, dict) else str(a) for a in args]   # a name component stays (#5346)
    return out | style


def name(key, kind="unit", fallback=None):
    """The text component of a unit, building or technology name (#5346): the key "aoe2mc.<kind>.<KEY>" (kind "unit":
    the AoE2 name of units.jsonl, "tech": the key of data/train.jsonl) with the English name (units.pretty, or the label
    of the menu) as fallback. The lang file of the pack makes these keys from the same tables."""
    from units import pretty
    return {"translate": f"aoe2mc.{kind}.{key}", "fallback": fallback or pretty(key)}


def plain(c):
    """The English text of a component of text() or name() (with no pack)."""
    if not isinstance(c, dict):
        return str(c)
    out = c.get("fallback", c.get("text", ""))
    for a in c.get("with", []):
        out = out.replace("%s", plain(a), 1)
    return out


def english(cmd):
    """Command cmd with its text component (the JSON at its end) as the plain English text, for logs and tests."""
    i = cmd.find("{")
    if i < 0:
        return cmd
    try:
        c = json.loads(cmd[i:])
    except ValueError:
        return cmd
    return cmd[:i] + json.dumps(plain(c)) if "translate" in c else cmd
