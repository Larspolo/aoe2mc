"""The Paper plugin (#3541): a unit that walks with a brain (a villager, a camel, a carrier) stops its brain also when
its order ends with "no path", not only when it arrives. Else it keeps its AI and strolls 20 to 45 blocks away: camel
scout -292 of de-64.3 after its rally walk to a gather point."""
import os
import re

PLUGIN = os.path.join(os.path.dirname(__file__), "..", "game", "plugin", "src", "main", "java", "aoe2mc", "AoePlugin.java")


def follow():
    with open(PLUGIN) as f:
        src = f.read()
    body = src[src.index("private void follow()"):]
    return body[:body.index("\n    }\n")]


def test_a_brain_stops_when_its_order_finds_no_path():
    body = follow()
    end = body[body.index("// it stays here"):body.index('"aoe2mc: no path "')]
    assert re.search(r"if \(brained\(mob\)\) \{[^\n]*\n\s*mob\.setAI\(false\);", end), end


def test_a_brain_stops_when_it_arrives():
    assert re.search(r"if \(brained\(mob\)\) \{\s*mob\.getPathfinder\(\)\.stopPathfinding\(\);.*?mob\.setAI\(false\);",
                     follow(), re.S)
