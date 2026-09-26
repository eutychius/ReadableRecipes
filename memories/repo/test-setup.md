# Test setup

- Tests run in the workspace venv `./venv` (created with `python -m venv venv`).
- Run tests: `.\scripts\run_tests.ps1` (activates venv, runs `python -m pytest tests -q`).
- Approval tests use the `approvaltests` package (PyPI name is NOT `pytest-approval-tests`).
  - Import: `from approvaltests.approvals import verify`; extension via `StackFrameNamer(extension=".html")`.
  - Approved files live in `tests/` as `<test>.approved.html`; a failing run writes `.received.html` (gitignored).
- `render.py` exposes `render_page(path) -> str` for tests; `render(path)` writes to `recipes_rendered/`.
