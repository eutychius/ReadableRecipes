"""Render recipe JSON files to printable poster HTML pages.

Usage: python render.py. Each recipes/*.json is rendered via
template.html into recipes_rendered/<name>.html. Stdlib only.
"""

from __future__ import annotations
import html
import json
import sys
from pathlib import Path

TEMPLATE_NAME = "template.html"   # lives next to render.py
OVERLAY = '<svg class="connectors" aria-hidden="true"></svg>'

class RecipeError(ValueError):
    """Invalid recipe data. Message is user-facing."""


def read_text(path: Path) -> str:
    """Read a UTF-8 file. RecipeError if the file is missing."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise RecipeError(f"file not found: {path}") from None


def load_recipe(path: Path) -> dict:
    """Parse recipe JSON. RecipeError on bad file/JSON."""
    try:
        data = json.loads(read_text(path))
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
    """Coerce an item (string or object) to (text, bold, uses)."""
    if isinstance(item, str):
        return item, False, None
    assert isinstance(item, dict), "item must be a string or object"
    return item["text"], item.get("bold", False), item.get("uses")


def valid_uses(uses: object, ingredients: list[object]) -> list[int]:
    """Resolve unique ingredient names in `uses` to their indices.

    An ingredient name refers to its first matching entry. Unknown names,
    duplicate entries, and non-string values are ignored.
    """
    if not isinstance(uses, list):
        return []
    ingredient_indices: dict[str, int] = {}
    for index, ingredient in enumerate(ingredients):
        if isinstance(ingredient, str):
            ingredient_indices.setdefault(ingredient, index)
    indices: list[int] = []
    for value in uses:
        if isinstance(value, str) and value in ingredient_indices:
            index = ingredient_indices[value]
            if index not in indices:
                indices.append(index)
    return indices


def build_connection_map(
    ingredients: list[object], steps: list[object]
) -> dict[int, list[int]]:
    """Map step index -> ingredient indices resolved from ingredient names.

    Lenient: non-list `uses`, unknown names, wrong-type, and duplicate
    entries are ignored. Steps with no valid ingredient are absent from
    the map.
    """
    mapping: dict[int, list[int]] = {}
    for step_index, step in enumerate(steps):
        _, _, uses = item_to_parts(step)
        indices = valid_uses(uses, ingredients)
        if indices:
            mapping[step_index] = indices
    return mapping


def render_item_box(item: object, attrs: str = "") -> str:
    """Render one item as a `<div class="box">` snippet (escaped).

    `attrs` is appended verbatim, e.g. data-index.
    """
    text, bold, _uses = item_to_parts(item)
    cls = "box bold" if bold else "box"
    return f'<div class="{cls}"{attrs}>{html.escape(text)}</div>'


def render_step_column(steps: list[object], mapping: dict[int, list[int]]) -> str:
    """Render the steps column: boxes joined with arrows.

    Steps in `mapping` get a data-uses attribute.
    """
    arrow = '<span class="arrow">↓</span>'
    boxes = []
    for step_index, step in enumerate(steps):
        indices = mapping.get(step_index)
        attrs = f' data-uses="{" ".join(map(str, indices))}"' if indices else ""
        boxes.append(render_item_box(step, attrs=attrs))
    return f'<div class="col steps">{arrow.join(boxes)}</div>'


def render_ingredient_column(ingredients: list[object]) -> str:
    """Render the ingredients column: one box per ingredient.

    Each box carries its index as data-index.
    """
    boxes = "".join(
        render_item_box(ingredient, attrs=f' data-index="{index}"')
        for index, ingredient in enumerate(ingredients)
    )
    return f'<div class="col ingredients">{boxes}</div>'


def render_section(section: dict) -> str:
    """Render one section: header + ingredients and steps columns.

    Adds an empty SVG overlay when the connection map is non-empty.
    """
    mapping = build_connection_map(section["ingredients"], section["steps"])
    return (
        f'<section class="section"><h2>{html.escape(section["name"])}</h2>'
        f'<div class="row">'
        f"{render_ingredient_column(section['ingredients'])}"
        f"{render_step_column(section['steps'], mapping)}"
        f"{OVERLAY if mapping else ''}"
        "</div></section>"
    )


def render_band(lines: list[str]) -> str:
    """Render the info band (escaped lines). Empty list -> ""."""
    if not lines:
        return ""
    band_lines = "".join(f'<span class="band-line">{html.escape(line)}</span>'
                         for line in lines)
    return f'<div class="band">{band_lines}</div>'


def fill_template(template: str, title: str, band: str, sections_html: str) -> str:
    """Replace <!--TITLE-->, <!--BAND-->, <!--SECTIONS--> in the template.

    RecipeError if a placeholder is missing.
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


def render_page(recipe_path: Path) -> str:
    """Load one recipe and build the full page HTML."""
    recipe = load_recipe(recipe_path)
    template = read_text(Path(__file__).parent / TEMPLATE_NAME)
    sections_html = "".join(render_section(section) for section in recipe["sections"])
    return fill_template(
        template,
        title=recipe["title"],
        band=render_band(recipe.get("band", [])),
        sections_html=sections_html,
    )


def render(recipe_path: Path) -> Path:
    """Build the page and write recipes_rendered/<name>.html.

    Schema validation is not enforced.
    """
    page = render_page(recipe_path)
    out_path = recipe_path.parent.parent / "recipes_rendered" / f"{recipe_path.stem}.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path


def main(argv: list[str]) -> int:
    """CLI: render each recipes/*.json. Returns 0, 1 (RecipeError), or 2 (usage)."""
    if argv:
        print(f"usage: python {Path(__file__).name}", file=sys.stderr)
        return 2
    recipes_dir = Path(__file__).parent / "recipes"
    if not recipes_dir.is_dir():
        raise RecipeError(f"folder not found: {recipes_dir}")
    out_paths = []
    for recipe_path in sorted(recipes_dir.glob("*.json")):
        try:
            out_paths.append(render(recipe_path))
        except RecipeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
    if out_paths:
        print("\n".join(map(str, out_paths)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
