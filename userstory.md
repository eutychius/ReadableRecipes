# ReadableRecipes — User Story

## User Story

As a **home cook**, I want to give a recipe as a small JSON file and get back a
**printable, poster-style HTML page** (look & feel like the Bananenschnitte
poster), so that I can print it out or save it as PDF (browser → "Print →
Save as PDF") and follow the recipe in the kitchen.

### Acceptance Criteria

- [ ] `python render.py recipe.json` produces `recipe.html` in the same folder.
- [ ] No third-party packages required (Python **stdlib only**, Python ≥ 3.9).
- [ ] The generated page shows:
  - [ ] Title (large, centered, uppercase)
  - [ ] Info band with up to 2 lines (e.g. "FÜR 1 BACKBLECH" / "HEISSLUFT • 200 °C • 12 MIN")
  - [ ] One block per section, each with:
    - [ ] Section name (left, bold, e.g. "TEIG")
    - [ ] Left column: one box per ingredient
    - [ ] Right column: one box per step, with arrows (↓) between the boxes
- [ ] An ingredient or step marked `"bold": true` is rendered bold/highlighted
      (e.g. `200 °C / 12 MIN BACKEN`, `1 STD KALT STELLEN`).
- [ ] Colors come from CSS variables in the template (green palette), so the
      look can be changed without touching the script.
- [ ] Layout is A4-portrait friendly for printing (works with browser
      Ctrl+P → Save as PDF).
- [ ] Invalid/missing fields fail with a readable error message (no traceback).

### Scope (explicitly NOT in v1)

- Bracket/connector lines from the ingredient column into the first step
  (v1 uses two independent columns per section).
- Automatic one-command PDF output (WeasyPrint/headless Chrome) — browser
  print is the PDF path for now.
- Multiple recipes / batch rendering.

---

## JSON Schema

A recipe is a single JSON object:

```json
{
  "title": "BANANENSCHNITTE",
  "band": ["FÜR 1 BACKBLECH", "HEISSLUFT • 200 °C • 12 MIN"],
  "sections": [
    {
      "name": "TEIG",
      "ingredients": ["180 g Zucker", "6 Eier"],
      "steps": ["Eier + Zucker aufschlagen"]
    }
  ]
}
```

### Field definitions

| Path                | Type                          | Required | Description                                              |
| ------------------- | ----------------------------- | -------- | -------------------------------------------------------- |
| `title`             | `string`                      | yes      | Poster title, rendered uppercase and large.              |
| `band`              | `array[string]` (0–2 entries) | no       | Info band lines under the title.                         |
| `sections`          | `array[section]` (≥ 1)        | yes      | The recipe sections, rendered top to bottom.             |
| `sections[].name`   | `string`                      | yes      | Section label, e.g. `TEIG`, `CREME`.                     |
| `sections[].ingredients` | `array[item]` (≥ 1)      | yes      | Ingredients, one box per entry.                          |
| `sections[].steps`  | `array[item]` (≥ 1)           | yes      | Instructions, one box per entry, arrows between boxes.   |

`item` is either:

- a plain `string`, or
- an object:

```json
{ "text": "200 °C / 12 MIN BACKEN", "bold": true }
```

| `item` field | Type     | Required | Description                        |
| ------------ | -------- | -------- | ---------------------------------- |
| `text`       | `string` | yes      | Box text.                          |
| `bold`       | `bool`   | no       | Render bold (default `false`).     |

### Full example (Bananenschnitte)

```json
{
  "title": "BANANENSCHNITTE",
  "band": ["FÜR 1 BACKBLECH", "HEISSLUFT • 200 °C • 12 MIN"],
  "sections": [
    {
      "name": "TEIG",
      "ingredients": ["180 g Zucker", "6 Eier", "50 g Mineralwasser", "180 g Weizenmehl 700"],
      "steps": [
        "Eier + Zucker aufschlagen",
        "Mineralwasser dazu",
        "Mehl vorsichtig unterheben",
        "auf Backblech streichen",
        { "text": "200 °C / 12 MIN BACKEN", "bold": true }
      ]
    },
    {
      "name": "CREME",
      "ingredients": ["400 g Milch", "40 g Zucker", "1 Pkg. Puddingpulver", "300 g pürierte Bananen (ca. 3 reife Bananen)", "4 Blatt Gelatine"],
      "steps": ["Pudding kochen", "kalt stellen", "pürierte Bananen einrühren", "Gelatine einarbeiten"]
    },
    {
      "name": "BELEGEN",
      "ingredients": ["8 Bananen (in Scheiben)", { "text": "MARILLENMARMELADE", "bold": true }],
      "steps": ["Biskuit mit Marmelade bestreichen", "Bananenscheiben darauflegen", "Creme darauf verteilen", { "text": "1 STD KALT STELLEN", "bold": true }]
    },
    {
      "name": "GLASUR",
      "ingredients": ["200 g Schokolade", "40 g Kokosfett"],
      "steps": ["Schokolade schmelzen + Kokosfett", { "text": "GLASUR AUFTRAGEN", "bold": true }]
    }
  ]
}
```

---

## Approach: HTML + CSS template, filled by Python stdlib

### How it works

```
recipe.json ──► render.py (stdlib only: json + html) ──► recipe.html
                                                         │
                                                  browser / Ctrl+P
                                                         │
                                                       PDF
```

1. **`template.html`** — a static HTML file containing *all* styling:
   - CSS variables for the palette (backgrounds, box borders, arrow color),
   - a `<style>` block defining `.poster`, `.band`, `.section`,
     `.ingredients` / `.steps` as two flex columns, `.box` styling,
     and `↓` arrows between step boxes,
   - a placeholder section marked by `<!--SECTIONS-->` (and `<!--TITLE-->`,
     `<!--BAND-->`) where the script injects markup.

2. **`render.py`** (~50 lines, stdlib only) —
   - reads and validates the JSON (missing/unknown fields → readable error),
   - walks the data and builds the inner HTML for each section
     (escaping all text with `html.escape`),
   - replaces the placeholders in `template.html`,
   - writes `recipe.html` next to the input file.

3. **PDF** — open `recipe.html`, Ctrl+P → "Save as PDF" (A4 portrait).
   No extra tooling needed.

### Why this is the simple version

- **Zero dependencies**: nothing to `pip install`, works on any machine with
  Python.
- **Layout in CSS, not code**: box sizes, gaps, colors, and the two-column
  structure live in the template — changing the look never means touching
  Python.
- **Simple layout choice**: each section renders two independent flex
  columns (ingredients left, steps right). No per-row alignment between
  columns and no bracket connectors, so any number of ingredients/steps
  works without layout math.
- **PDF is decoupled**: the browser print path is good enough for v1; if a
  one-command PDF is ever wanted, the same template can be fed to
  WeasyPrint or headless Chrome without redesign.

### Planned file layout (v1)

```
ReadableRecipes/
├── userstory.md        ← this file
├── render.py           ← CLI: python render.py recipe.json
├── template.html       ← styling + placeholders
├── bananenschnitte.json ← sample recipe (the poster)
└── bananenschnitte.html ← generated output
```
