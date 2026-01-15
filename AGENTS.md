# Repository Guidelines

## Project Structure & Module Organization

```
auto-counts-documents-and-product-number/
├── run.ps1                 # PowerShell 入口腳本
├── pyproject.toml          # uv 專案設定
├── template.xlsx           # Excel 模板（B3=支數, C3=張數）
├── src/doc_processor/      # Python 核心模組
│   ├── cli.py              # CLI 入口
│   ├── phase1.py           # Phase 1 邏輯
│   ├── phase2.py           # Phase 2 邏輯
│   ├── pdf_parser.py       # PDF 解析
│   ├── excel_writer.py     # Excel 寫入
│   └── logger.py           # Log 處理
├── tests/                  # pytest 測試
│   ├── fixtures/           # 測試用 PDF 樣本
│   └── test_*.py           # 測試檔案
├── input/                  # 放入當天 PDF（gitignore）
├── output/                 # 輸出結果（gitignore）
├── PRD.md                  # 產品需求文件
└── CLAUDE.md               # Claude Code 指南
```

## Build, Test, and Development Commands

```powershell
# 執行 Phase 1（合併 PDF）
.\run.ps1 phase1

# 執行 Phase 2（產生 Excel）
.\run.ps1 phase2

# 一鍵執行全部
.\run.ps1 all

# 直接用 Python 執行
uv run python -m doc_processor phase1
uv run python -m doc_processor phase2
uv run python -m doc_processor all

# 執行測試
uv run pytest tests/ -v

# 安裝依賴（含開發工具）
uv sync --extra dev
```

## Coding Style & Naming Conventions

- **Python**: 4-space indentation, `snake_case` for modules/functions, `PascalCase` for classes
- **PowerShell**: `Verb-Noun` function names
- **Encoding**: UTF-8 (with BOM for PowerShell scripts)
- Output filenames must follow PRD patterns to keep Phase 2 deterministic

## Testing Guidelines

- Framework: pytest
- Test files: `test_*.py` in `tests/`
- Fixtures: `tests/fixtures/` (redacted PDF samples)
- Current status: 30 tests, all passing

```powershell
# Run all tests
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_pdf_parser.py -v
```

## Processing Notes

- Multi-order PDFs are parsed per page; consecutive pages with the same purchase order and page sequence (1/2, 2/2) are merged.
- Phase 2 purchase order page detection keywords: 採購日期:, 廠商:, 承製廠商簽回
- Missing required documents (goods receipt or receipt inspection) skip the group.

## Commit & Pull Request Guidelines

- Use Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`
- Include summary of behavior changes
- Reference PRD section when applicable
- Include sample inputs/outputs for PDF/Excel changes

Example:
```
feat(phase1): 新增多採購單分組支援

- 依採購單號分組合併 PDF
- 請購單透過採購單間接關聯
```

## Security & Configuration Tips

- Do not commit real vendor documents or sensitive purchase data
- `input/` and `output/` are gitignored
- Test fixtures should use redacted/sanitized data

## Agent-Specific Instructions

- Follow PRD constraints strictly: **no OCR, no subfolder recursion, no fallback heuristics**
- Never modify files under `input/`; always write results to `output/`
- When extraction fails, log the error and skip—do not guess or use backup rules
- Log files are written to `output/YYYYMMDD_HHMMSS.log`
