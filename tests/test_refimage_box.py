"""tools/refimage.py box: the infobox values of a wiki page as plain text (#3665), with no network."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import refimage  # noqa: E402

PAGE = """{{For|the unit in AoE2|Hoplite}}
{{Infobox AoE2 unit
|Name = Hoplite
|Image = <gallery>
HopliteDE.png|Definitive
</gallery>
|Civilization = All except [[Persians (Age of Empires)|Persians]]
|Age = {{1icons|Bronze Age}}
|Food = 60
|UpCost = [[File:Phalanxupgrade.png|22px]] {{resources|food = 300|gold = 100}}
|Speed = {{tt|0.87|0.9 before Return of Rome}}
|Required = Two of the following:<br />{{1icons|Barracks}}<br />{{1icons|Dock}}
}}
'''Hoplite''' text.
|Food = 999
"""


def test_box_reads_the_values_of_the_first_infobox():
    b = refimage.box(PAGE)
    assert b["Civilization"] == "All except Persians" and b["Age"] == "Bronze Age" and b["Food"] == "60"
    assert b["UpCost"] == "300 food, 100 gold" and b["Speed"] == "0.87"
    assert b["Required"] == "Two of the following:, Barracks, Dock"


def test_box_reads_a_techbox_and_a_page_without_box():
    assert refimage.box("{{Techbox\n|Name = Toolworking\n|Food = 100\n}}") == {"Name": "Toolworking", "Food": "100"}
    assert refimage.box("no template") == {}
