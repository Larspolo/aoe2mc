"""
Check block states, entity IDs, biomes and sound events against the Minecraft data in tools/mcdata/<version>.json.

    import mcvalid
    mcvalid.block_error("minecraft:oak_fence[east=true]")    # None if valid, else a message
"""
import functools
import json
import os

DEFAULT_VERSION = "26.3"        # the block and entity names in the code and in the output (#428)
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcdata")


@functools.lru_cache(maxsize=None)
def data(version=DEFAULT_VERSION):
    with open(os.path.join(DATA_DIR, f"{version}.json")) as f:
        return json.load(f)


def block_error(state, version=DEFAULT_VERSION):
    """Return None if `state` (for example "minecraft:stairs[facing=north]") is a valid block state, else the problem."""
    name = state.split(":", 1)[1] if ":" in state else state
    base, _, props = name.partition("[")
    spec = data(version)["blocks"].get(base)
    if spec is None:
        return f"unknown block '{base}'"
    for kv in filter(None, props.rstrip("]").split(",")):
        key, _, value = kv.partition("=")
        if key not in spec:
            return f"'{base}' has no property '{key}' (has {sorted(spec)})"
        if value not in spec[key]:
            return f"'{base}' property '{key}' cannot be '{value}' (allowed {spec[key]})"
    return None


def entity_error(entity_id, version=DEFAULT_VERSION):
    name = entity_id.split(":", 1)[1] if ":" in entity_id else entity_id
    return None if name in data(version)["entities"] else f"unknown entity '{name}'"


def biome_error(biome, version=DEFAULT_VERSION):
    name = biome.split(":", 1)[1] if ":" in biome else biome
    return None if name in data(version)["biomes"] else f"unknown biome '{name}'"


def sound_error(sound, version=DEFAULT_VERSION):
    name = sound.split(":", 1)[1] if ":" in sound else sound
    return None if name in data(version)["sounds"] else f"unknown sound '{name}'"


def predicate_error(d):
    """Return None if the predicate dict `d` has the 26.3 keys, else the problem (#3139): "type", not "condition";
    an entity predicate has namespaced keys ("minecraft:vehicle"), and a vehicle or passenger is an entity predicate."""
    if isinstance(d, list):
        return next(filter(None, map(predicate_error, d)), None)
    if "condition" in d:
        return "key 'condition': 26.3 uses 'type'"
    if "type" not in d:
        return "no key 'type'"
    terms = d.get("terms", []) + ([d["term"]] if "term" in d else [])
    return next(filter(None, map(predicate_error, terms)), None) or (
        entity_predicate_error(d["predicate"]) if d["type"].endswith("entity_properties") else None)


def entity_predicate_error(p):
    for key, value in p.items():
        if ":" not in key:
            return f"entity predicate key '{key}' has no namespace (26.3: 'minecraft:{key}')"
        if key.split(":")[1] in ("vehicle", "passenger", "targeted_entity") and (err := entity_predicate_error(value)):
            return err
    return None


def invalid_states(states, version=DEFAULT_VERSION):
    """{state: problem} for all invalid states in `states`."""
    out = {}
    for s in states:
        err = block_error(s, version)
        if err:
            out[s] = err
    return out
