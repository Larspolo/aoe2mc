"""rmap.CREATE_OBJECT has one line per create_object attribute that rmap.objects reads (#4224): parallel random map
tickets add lines in alphabetical order, not to the end of one set."""
import inspect
import re

import rmap


def test_the_attributes_are_sorted_and_unique():
    assert list(rmap.CREATE_OBJECT) == sorted(set(rmap.CREATE_OBJECT))


def test_each_attribute_that_objects_reads_has_its_line():
    source = inspect.getsource(rmap.objects)
    read = set(re.findall(r'"(\w+)" in attrs|attrs\["(\w+)"\]', source))
    read = {a for pair in read for a in pair if a}
    assert read - set(rmap.CREATE_OBJECT) == set(), "add a line to rmap.CREATE_OBJECT for each new attribute"


def test_an_attribute_that_is_not_read_gives_a_warning():
    warns = []
    name = next(iter(rmap.OBJECTS))
    rmap.objects([("create_object", [name], {"no_such_attribute": []})], dict(rmap.OBJECTS), rmap.np.zeros((20, 20), int), [],
                 rmap.np.random.default_rng(1), warns.append)
    assert "create_object: no_such_attribute is not read yet" in warns
