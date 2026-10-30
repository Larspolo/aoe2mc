"""The unit abilities of the Paper plugin (#4589): one class per ability that implements Ability, and one line per
class in the services file (ServiceLoader). AoePlugin.java has no command line of an ability, so that parallel
ability PRs do not conflict there. The Java files are read as text."""
import glob
import os
import re

SRC = os.path.join(os.path.dirname(__file__), "..", "game", "plugin", "src", "main")
JAVA = os.path.join(SRC, "java", "aoe2mc")
SERVICES = os.path.join(SRC, "resources", "META-INF", "services", "aoe2mc.Ability")


def classes():
    """The class name and the text of each Java file of the package."""
    return {os.path.basename(f)[:-5]: open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(JAVA, "*.java"))}


def lines():
    return [ln.strip() for ln in open(SERVICES, encoding="utf-8") if ln.strip() and not ln.startswith("#")]


def abilities():
    return sorted(n for n, text in classes().items() if re.search(r"\bclass\s+" + n + r"\s+implements\s+[\w, ]*\bAbility\b", text))


def test_each_ability_class_has_its_line_in_the_services_file():
    assert abilities()
    assert sorted(set(abilities()) - {ln.removeprefix("aoe2mc.") for ln in lines()}) == []


def test_each_line_names_a_public_ability_class_once():
    known = classes()
    assert len(lines()) == len(set(lines()))
    for ln in lines():
        assert ln.startswith("aoe2mc."), ln
        name = ln.removeprefix("aoe2mc.")
        assert name in abilities(), ln
        assert re.search(r"\bpublic\s+(final\s+)?class\s+" + name + r"\b", known[name]), f"{ln}: ServiceLoader needs a public class"


def test_the_plugin_dispatches_no_command_of_an_ability_itself():
    plugin = classes()["AoePlugin"]
    for name in abilities():
        cmd = re.search(r'String name\(\)\s*\{\s*return\s+"([^"]+)"', classes()[name]).group(1)
        assert f'args[0].equals("{cmd}")' not in plugin, f"aoe {cmd}: its command belongs in {name}.java"
