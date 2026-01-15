# Repository Guidelines

## Project Structure & Module Organization
- `input/`: drop the same-day PDF documents here; keep the folder flat (no subfolders).
- `output/`: merged PDFs and generated Excel summaries are written here.
- `PRD.md`: requirements, phases, regex rules, and processing order.
- `template.xlsx` and `samples.xlsx`: Excel template and example data for validation.
- Root samples: keep any sample PDFs/images minimal and sanitized.

## Build, Test, and Development Commands
There are no runnable scripts checked in yet. When automation is added, document the exact commands here. The PRD calls for a PowerShell wrapper plus a Python core; examples to aim for:

```powershell
# Planned entrypoints (add once scripts exist)
.\run.ps1 phase1
.\run.ps1 phase2
.\run.ps1 all
```

## Coding Style & Naming Conventions
- Save scripts in UTF-8 BOM as required by the PRD.
- Python: 4-space indentation, `snake_case` for modules/functions, `PascalCase` for classes.
- PowerShell: `Verb-Noun` function names and descriptive script filenames.
- Output filenames must follow the patterns defined in `PRD.md` to keep Phase 2 deterministic.

## Testing Guidelines
No tests or framework are present yet. If you add tests, prefer `pytest`, name files `test_*.py`, and keep PDF fixtures in a dedicated `tests/fixtures/` folder with redacted data. Document the test command in this section once it exists.

## Commit & Pull Request Guidelines
This folder is not a Git repository, so no commit convention is established. If you initialize Git, use Conventional Commits (e.g., `feat: add phase1 parser`) and include:
- a short summary of behavior changes
- linked PRD section or issue ID
- sample inputs or screenshots when PDF/Excel output changes

## Security & Configuration Tips
- Do not commit real vendor documents or sensitive purchase data.
- Keep `input/` and `output/` local-only; add fixtures only if redacted and minimal.

## Agent-Specific Instructions
- Follow the PRD constraints strictly: no OCR, no subfolder recursion, and no fallback heuristics.
- Never modify files under `input/`; always write results to `output/`.
