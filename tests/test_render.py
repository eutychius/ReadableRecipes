"""Unit tests for the small building blocks in render.py.

The approval test in ``test_render.py`` checks the full page.
These tests check one function at a time. They run fast and show
a clear failure point when one block misbehaves.
"""

import pytest

import render


def test_item_to_parts_object():
    """An object item gives text, bold, and uses."""
    item = {"text": "backen", "bold": True, "uses": [1]}
    assert render.item_to_parts(item) == ("backen", True, [1])


def test_build_connection_map_filters_bad_entries():
    """Bad entries drop out. Valid ones keep their order.

    - out-of-range index (5) -> dropped
    - duplicate (0) -> first occurrence wins
    - wrong type ("x", True) -> dropped
    - empty result (step 2) -> step is absent from the map
    """
    ingredients = ["a", "b", "c"]
    steps = [
        {"text": "s0", "uses": [2, 0, 0, 5, "x", True, 1]},
        "plain step",
        {"text": "s2", "uses": [9]},
    ]
    mapping = render.build_connection_map(ingredients, steps)
    assert mapping == {0: [2, 0, 1]}


def test_fill_template_raises_without_placeholders():
    """A template without the placeholders is out of sync."""
    with pytest.raises(render.RecipeError, match="TITLE"):
        render.fill_template("<html></html>", "T", "", "")
