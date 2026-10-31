"""Texts as Minecraft `translate` components (#5344): a lang file of a resource pack can give a key in another
language; with no pack the client shows the English `fallback` of game/data/texts.jsonl."""
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
        out["with"] = [str(a) for a in args]
    return out | style
