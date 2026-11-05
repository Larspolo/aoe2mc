"""xs_mc: the XS object counts and the civilization as datapack commands (#5695)."""
import sys

import xs
import xs_mc

sys.path.insert(0, "game")
import xs_host  # noqa: E402

SEL = "@e[tag=aoe2mc.p1,tag=aoe2mc.t83,tag=!aoe2mc.mount]"


def compiled(text, civs=None):
    files, _, _, warnings = xs_mc.compile(xs.parse(text), text, civs)
    assert warnings == []
    return files


def test_a_literal_count_is_one_selector():
    files = compiled("int a = 0; void main() { a = xsGetObjectCount(1, 83) + xsGetObjectCountTotal(1, 83); }")
    lines = files[f"{xs_mc.DIR}/main.mcfunction"].splitlines()
    assert sum(f"if entity {SEL}" in x and x.startswith("execute store result score") for x in lines) == 2
    assert f"{xs_mc.DIR}/count.mcfunction" not in files


def test_a_computed_player_uses_the_macro_function():
    files = compiled("int p = 1; int a = 0; void main() { a = xsGetObjectCount(p + 1, 83); }")
    lines = files[f"{xs_mc.DIR}/main.mcfunction"].splitlines()
    assert any(x.startswith(f"execute store result storage {xs_mc.STORE} count.p int 1 run") for x in lines)
    assert f"data modify storage {xs_mc.STORE} count.id set value 83" in lines
    assert any(x.endswith(f"run function aoe2mc:xs/count with storage {xs_mc.STORE} count") for x in lines)
    macro = files[f"{xs_mc.DIR}/count.mcfunction"].strip()
    assert macro.startswith("$return run execute if entity @e[") and "tag=aoe2mc.p$(p)" in macro
    assert "tag=aoe2mc.t$(id)" in macro and "tag=!aoe2mc.mount" in macro


def test_the_civilization_is_the_id_of_the_converted_player():
    files = compiled("int c = 0; void main() { c = xsGetPlayerCivilization(2); }", {1: "FRANKS", 2: "BRITONS"})
    want = xs_host.civ_id("BRITONS")
    lines = files[f"{xs_mc.DIR}/main.mcfunction"].splitlines()
    assert want > 0 and any(x.startswith("scoreboard players set #x") and x.endswith(f" {want}") for x in lines)
