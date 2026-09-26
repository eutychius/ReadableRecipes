"""ReadableRecipes — render a recipe JSON file to a printable poster HTML page.

Usage:
    python render.py recipe.json

Reads `recipe.json` (expected shape: schema in `userstory.md`),
fills `template.html` (placeholders: <!--TITLE-->, <!--BAND-->, <!--SECTIONS-->)
and writes `recipe.html` next to the input file.

Stdlib only (Python >= 3.9): json, html, pathlib, sys.
No third-party packages. PDF is produced via browser print (Ctrl+P).
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

TEMPLATE_NAME = "template.html"   # lives next to render.py
OUTPUT_NAME = "recipe.html"       # written next to the input file


class RecipeError(ValueError):
    """Invalid recipe data. Message is user-facing (no traceback)."""


def load_recipe(path: Path) -> dict:
    """Read and parse the recipe JSON file.

    Raises RecipeError if the file is missing, the JSON is invalid
    (message includes line/column info), or the top level is not a
    JSON object.
    """
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RecipeError(f"file not found: {path}") from None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RecipeError(
            f"invalid JSON in {path.name} "
            f"(line {exc.lineno}, column {exc.colno}): {exc.msg}"
        ) from None
    if not isinstance(data, dict):
        raise RecipeError(
            f"invalid recipe in {path.name}: "
            f"top level must be a JSON object, got {type(data).__name__}"
        )
    return data


def item_to_parts(item: object) -> tuple[str, bool, object | None]:
    """Coerce one item to (text, bold, uses).

    A plain string item is (text, False, None). An object item is
    (item["text"], item.get("bold", False), item.get("uses")).
    Pure extraction: uses is the raw value, if any. This function
    does not check the value. The expected shape is the schema in
    userstory.md.
    """
    if isinstance(item, str):
        return item, False, None
    assert isinstance(item, dict), "item must be a string or object"
    return item["text"], item.get("bold", False), item.get("uses")


def build_connection_map(
    ingredients: list[object], steps: list[object]
) -> dict[int, list[int]]:
    """Build the per-section connection map: step index -> ingredient indices.

    The map holds one entry per step that has at least one valid
    reference. Each value is the step's `uses` list, reduced to
    in-range integers in their original order.

    Filtering is lenient (userstory-arrows.md, decision 3): no
    validation and no error. Per step:
    - a missing `uses` (plain string step) or a non-list `uses`
      -> the step is absent from the map;
    - wrong-type entries (non-int, bool, string, null, ...)
      -> ignored;
    - out-of-range indices (< 0 or >= ingredient count) -> ignored;
    - duplicates -> dropped, first occurrence wins.

    A step whose `uses` list yields no valid index is absent from
    the map, so the renderer draws no connector for it.
    """
    count = len(ingredients)
    mapping: dict[int, list[int]] = {}
    for step_index, step in enumerate(steps):
        _text, _bold, uses = item_to_parts(step)
        if not isinstance(uses, list):
            continue
        indices: list[int] = []
        for value in uses:
            if isinstance(value, bool) or not isinstance(value, int):
                continue
            if value < 0 or value >= count:
                continue
            if value in indices:
                continue
            indices.append(value)
        if indices:
            mapping[step_index] = indices
    return mapping


def render_item_box(item: object, attrs: str = "") -> str:
    """Render one item as a `<div class="box">…</div>` snippet.

    The text is escaped with html.escape; when bold is set the box
    gets an extra "bold" class (styled in the template). `attrs` is
    an optional attribute string for the box (for example a
    data-index for the connector script); it is emitted as-is.
    """
    text, bold, _uses = item_to_parts(item)
    cls = "box bold" if bold else "box"
    return f'<div class="{cls}"{attrs}>{html.escape(text)}</div>'


def render_step_column(steps: list[object], mapping: dict[int, list[int]]) -> str:
    """Render the right column: one box per step, arrows between boxes.

    Boxes are joined with <span class="arrow">↓</span> and wrapped
    in <div class="col steps">. A step that appears in `mapping`
    (2c) carries its valid ingredient indices as a
    space-separated data-uses attribute; other steps carry none.
    """
    arrow = '<span class="arrow">↓</span>'
    boxes = []
    for step_index, step in enumerate(steps):
        indices = mapping.get(step_index)
        attrs = f' data-uses="{" ".join(map(str, indices))}"' if indices else ""
        boxes.append(render_item_box(step, attrs=attrs))
    return f'<div class="col steps">{arrow.join(boxes)}</div>'


def render_ingredient_column(ingredients: list[object]) -> str:
    """Render the left column: one box per ingredient.

    Boxes are stacked without connectors and wrapped in
    <div class="col ingredients">. Each box carries its index
    within the section as data-index (2c) for the connector script.
    """
    boxes = "".join(
        render_item_box(ingredient, attrs=f' data-index="{index}"')
        for index, ingredient in enumerate(ingredients)
    )
    return f'<div class="col ingredients">{boxes}</div>'


def render_section(section: dict) -> str:
    """Render one section block: header + two independent flex columns.

    Emits <section class="section"> with an <h2> header (escaped
    section name) and the two columns side by side: ingredients on
    the left, steps on the right.

    A section whose connection map (2b) is non-empty also gets an
    empty <svg class="connectors"> layer inside the row (2d). The
    inline script in template.html measures the boxes and fills the
    SVG with paths. A section without references renders exactly as
    before: no overlay element at all.
    """
    name = html.escape(section["name"])
    mapping = build_connection_map(
        section["ingredients"], section["steps"]
    )
    ingredients = render_ingredient_column(section["ingredients"])
    steps = render_step_column(section["steps"], mapping)
    overlay = '<svg class="connectors" aria-hidden="true"></svg>' if mapping else ""
    return (
        '<section class="section">'
        f"<h2>{name}</h2>"
        "<div class=\"row\">"
        f"{ingredients}"
        f"{steps}"
        f"{overlay}"
        "</div>"
        "</section>"
    )


def render_band(lines: list[str]) -> str:
    """Render the info band under the title (0-2 lines).

    Emits one <span class="band-line"> per line (escaped), wrapped
    in <div class="band">. An empty list yields an empty string so
    the template placeholder is simply removed.
    """
    if not lines:
        return ""
    band_lines = "".join(f'<span class="band-line">{html.escape(line)}</span>'
                         for line in lines)
    return f'<div class="band">{band_lines}</div>'


def fill_template(template: str, title: str, band: str, sections_html: str) -> str:
    """Replace the placeholders in template.html.

    <!--TITLE-->    -> escaped title
    <!--BAND-->     -> band markup (may be empty)
    <!--SECTIONS--> -> concatenated section markup

    The band and section markup is already escaped by the render_*
    helpers, so it is inserted verbatim. If a placeholder is missing,
    the template is out of sync with this script -> RecipeError.
    """
    replacements = (
        ("<!--TITLE-->", html.escape(title)),
        ("<!--BAND-->", band),
        ("<!--SECTIONS-->", sections_html),
    )
    result = template
    for placeholder, value in replacements:
        if placeholder not in result:
            raise RecipeError(
                f"template is out of sync: missing placeholder {placeholder}"
            )
        result = result.replace(placeholder, value)
    return result


def render(recipe_path: Path) -> Path:
    """End-to-end pipeline: load -> build HTML -> write output.

    The template lives next to this script (Path(__file__).parent).
    The output file (OUTPUT_NAME) is written next to the input file
    as utf-8 and its path is returned.

    NOTE: schema validation is temporarily not enforced — the data is
    consumed as-is (see userstory.md for the expected shape).
    """
    recipe = load_recipe(recipe_path)
    template_path = Path(__file__).parent / TEMPLATE_NAME
    try:
        template = template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RecipeError(f"file not found: {template_path}") from None
    sections_html = "".join(render_section(section) for section in recipe["sections"])
    page = fill_template(
        template,
        title=recipe["title"],
        band=render_band(recipe.get("band", [])),
        sections_html=sections_html,
    )
    out_path = recipe_path.parent / OUTPUT_NAME
    out_path.write_text(page, encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    """CLI entry point: `python render.py recipe.json`.

    Returns 0 on success (prints the output path), 1 on RecipeError
    (prints the message), 2 on bad usage. No traceback leaks.
    """
    if len(argv) != 1:
        print(f"usage: python {Path(__file__).name} <recipe.json>", file=sys.stderr)
        return 2
    try:
        out_path = render(Path(argv[0]))
    except RecipeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
