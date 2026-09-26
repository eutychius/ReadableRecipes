"""Approval test for the rendered bananenschnitte poster.

The test builds the page with ``render.render_page`` for
``recipes/bananenschnitte.json``. It then compares the page to the
approved file that sits next to this test.

If the output changes, the test fails and writes a ``.received`` file.
Review the received file. Then rename it to the approved name to
accept the change.
"""

from pathlib import Path

from approvaltests.approvals import verify
from approvaltests.namer.stack_frame_namer import StackFrameNamer

import render

RECIPE_PATH = (
    Path(__file__).resolve().parents[1] / "recipes" / "bananenschnitte.json"
)


def test_bananenschnitte_html():
    """Approve the exact poster HTML for the bananenschnitte recipe."""
    page = render.render_page(RECIPE_PATH)
    verify(page, namer=StackFrameNamer(extension=".html"))
