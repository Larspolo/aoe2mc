"""The #include lines of an AoE2 random map script (#3058): random_map.def has the constants, the XS files are not run."""
import pytest
from test_rmap import SCRIPT, make


def includes(notes):
    return [n for n in notes if n.startswith("#include")]


@pytest.mark.parametrize("line", ["#include_drs random_map.def\n", "#include_drs random_map.def 54000\n"])
def test_an_include_drs_before_the_first_section_is_the_same_land(line):
    assert make(3, script=line + SCRIPT)[0] == make(3)[0]


def test_an_includexs_gives_the_same_land_and_one_warning_that_names_the_file():
    d, notes = make(3, script=SCRIPT.replace("<LAND_GENERATION>", "#includeXS triggers.xs\n<LAND_GENERATION>", 1))
    assert d == make(3)[0]
    assert includes(notes) == ["#includeXS triggers.xs is not read"]


def test_random_map_def_gives_no_warning():
    assert includes(make(3, script="#include_drs random_map.def\n" + SCRIPT)[1]) == []


def test_an_include_in_an_inactive_branch_is_skipped():
    d, notes = make(3, script="if NOT_DEFINED\n#includeXS triggers.xs\nendif\n" + SCRIPT)
    assert d == make(3)[0] and includes(notes) == []
