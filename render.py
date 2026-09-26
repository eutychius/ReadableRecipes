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


def item_to_parts(item: object) -> tuple[str, bool]:
    """Coerce one item to (text, bold).

    A plain string item is (text, False). An object item is
    (item["text"], item.get("bold", False)).
    Pure extraction — the expected shape is the schema in userstory.md.
    """
    if isinstance(item, str):
        return item, False
    assert isinstance(item, dict), "item must be a string or object"
    return item["text"], item.get("bold", False)


def render_item_box(item: object) -> str:
    """Render one item as a `<div class="box">…</div>` snippet.

    The text is escaped with html.escape; when bold is set the box
    gets an extra "bold" class (styled in the template).
    """
    text, bold = item_to_parts(item)
    cls = "box bold" if bold else "box"
    return f'<div class="{cls}">{html.escape(text)}</div>'


def render_step_column(steps: list[object]) -> str:
    """Render the right column: one box per step, arrows between boxes.

    Boxes are joined with <span class="arrow">↓</span> and wrapped
    in <div class="col steps">.
    """
    arrow = '<span class="arrow">↓</span>'
    boxes = arrow.join(render_item_box(step) for step in steps)
    return f'<div class="col steps">{boxes}</div>'


def render_ingredient_column(ingredients: list[object]) -> str:
    """Render the left column: one box per ingredient.

    Boxes are stacked without connectors and wrapped in
    <div class="col ingredients">.
    """
    boxes = "".join(render_item_box(ingredient) for ingredient in ingredients)
    return f'<div class="col ingredients">{boxes}</div>'


def render_section(section: dict) -> str:
    """Render one section block: header + two independent flex columns.

    Emits <section class="section"> with an <h2> header (escaped
    section name) and the two columns side by side: ingredients on
    the left, steps on the right. No bracket connectors in v1
    (explicitly out of scope).
    """
    name = html.escape(section["name"])
    ingredients = render_ingredient_column(section["ingredients"])
    steps = render_step_column(section["steps"])
    return (
        '<section class="section">'
        f"<h2>{name}</h2>"
        "<div class=\"row\">"
        f"{ingredients}"
        f"{steps}"
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
