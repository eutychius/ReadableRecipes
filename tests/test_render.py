"""Unit tests for the small building blocks in render.py."""

import pytest
import render


def test_item_to_parts_object():
    """An object item gives text, bold, and uses."""
    item = {"text": "backen", "bold": True, "uses": ["Mehl"]}
    assert render.item_to_parts(item) == ("backen", True, ["Mehl"])


def test_build_connection_map_filters_bad_entries():
    """Bad ingredient names drop out. Valid ones keep their order.

    - unknown ingredient ("d") -> dropped
    - duplicate ("a") -> first occurrence wins
    - wrong type (2, True) -> dropped
    - empty result (step 2) -> step is absent from the map
    """
    ingredients = ["a", "b", "c", "a"]
    steps = [
        {"text": "s0", "uses": ["c", "a", "a", "d", 2, True, "b"]},
        "plain step",
        {"text": "s2", "uses": ["missing"]},
    ]
    mapping = render.build_connection_map(ingredients, steps)
    assert mapping == {0: [2, 0, 1]}


def test_fill_template_raises_without_placeholders():
    """A template without the placeholders is out of sync."""
    with pytest.raises(render.RecipeError, match="TITLE"):
        render.fill_template("<html></html>", "T", "", "")


def test_item_to_parts_string():
    """A plain string gives (text, no bold, no uses)."""
    assert render.item_to_parts("Eier") == ("Eier", False, None)


def test_item_to_parts_missing_bold_defaults_false():
    """An object without "bold" gets bold=False."""
    assert render.item_to_parts({"text": "Eier"}) == ("Eier", False, None)


def test_render_item_box_escapes_and_applies_attrs():
    """Text is escaped; bold adds a class; attrs are emitted as-is."""
    plain = render.render_item_box("Eier < 100 g")
    assert plain == '<div class="box">Eier &lt; 100 g</div>'
    bold = render.render_item_box(
        {"text": "BACKEN", "bold": True}, attrs=' data-uses="0 2"'
    )
    assert bold == (
        '<div class="box bold" data-uses="0 2">BACKEN</div>'
    )


def test_render_band_empty_list_yields_empty_string():
    """No lines -> no band markup at all."""
    assert render.render_band([]) == ""


def test_render_band_escapes_lines():
    """One span per line, each line escaped."""
    html = render.render_band(["FÜR 1 BACKBLECH", "A < B"])
    assert html == (
        '<div class="band">'
        '<span class="band-line">FÜR 1 BACKBLECH</span>'
        '<span class="band-line">A &lt; B</span>'
        '</div>'
    )


def test_render_section_overlay_only_with_valid_refs():
    """An SVG overlay appears only when the section has refs."""
    with_refs = render.render_section(
        {
            "name": "S1",
            "ingredients": ["a", "b"],
            "steps": [{"text": "s", "uses": ["b"]}],
        }
    )
    assert '<svg class="connectors" aria-hidden="true"></svg>' in with_refs
    without_refs = render.render_section(
        {"name": "S2", "ingredients": ["a"], "steps": ["plain"]}
    )
    assert "connectors" not in without_refs


def test_render_step_column_arrows_and_data_uses():
    """Boxes join with arrows; only mapped steps carry data-uses."""
    steps = [
        {"text": "s0", "uses": ["b", "a"]},
        "s1",
        {"text": "s2", "bold": True},
    ]
    mapping = render.build_connection_map(["a", "b"], steps)
    html = render.render_step_column(steps, mapping)
    assert html == (
        '<div class="col steps">'
        '<div class="box" data-uses="1 0">s0</div>'
        '<span class="arrow">↓</span>'
        '<div class="box">s1</div>'
        '<span class="arrow">↓</span>'
        '<div class="box bold">s2</div>'
        "</div>"
    )


def test_render_ingredient_column_indices_and_no_arrows():
    """Each box gets its data-index; boxes stack without arrows."""
    ingredients = ["a", "b", "c"]
    html = render.render_ingredient_column(ingredients)
    assert html == (
        '<div class="col ingredients">'
        '<div class="box" data-index="0">a</div>'
        '<div class="box" data-index="1">b</div>'
        '<div class="box" data-index="2">c</div>'
        "</div>"
    )
