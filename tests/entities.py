"""Test helpers for entities, in a module with its own name: `framework/tests` also has a `conftest`."""


def entity_ids(nbt_or_desc):
    """All entity IDs of an entity and its passengers (riders)."""
    out = [str(nbt_or_desc["id"])]
    for p in nbt_or_desc.get("Passengers", []):
        out += entity_ids(p)
    return out
