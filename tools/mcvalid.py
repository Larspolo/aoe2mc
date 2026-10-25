"""
Check block states, entity IDs and biomes against the Minecraft data in tools/mcdata/<version>.json.

    import mcvalid
    mcvalid.block_error("minecraft:oak_fence[east=true]")    # None if valid, else a message
"""
import functools
import json
import os

DEFAULT_VERSION = "1.21.1"      # the version that aoe2mc.DATA_VERSION writes
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


def invalid_states(states, version=DEFAULT_VERSION):
    """{state: problem} for all invalid states in `states`."""
    out = {}
    for s in states:
        err = block_error(s, version)
        if err:
            out[s] = err
    return out
