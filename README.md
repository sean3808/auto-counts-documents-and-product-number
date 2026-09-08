# doc-processor

採購單關聯單據重組與單據明細產生器。將當天所有 PDF 單據自動蓋章、依採購單號分組合併，並自動填入 Excel 明細。

## 需求

- Windows 11
- Python 3.13+
- uv 套件管理器

## 安裝

```powershell
uv sync --extra dev
```

## 使用方式

**最簡單：雙擊 `run.bat`**（自動執行全部流程）

或用 PowerShell：

```powershell
# Phase 0: PDF 蓋章
.\run.ps1 phase0

# Phase 1: 合併 PDF
.\run.ps1 phase1

# Phase 2: 產生 Excel 明細
.\run.ps1 phase2

# 一鍵執行（預設值）：phase0 → phase1 → phase2
.\run.ps1 all

# 不帶參數時預設為 all
.\run.ps1
```

或用 Python 執行：

```powershell
uv run python -m doc_processor phase0
uv run python -m doc_processor phase1
uv run python -m doc_processor phase2
uv run python -m doc_processor all
```

## 輸入與輸出

- 將來源 PDF 放在 `input/`（不遞迴子資料夾）。
- 印章圖片放在 `印章/removebg/`（需預先去背的 PNG）。
- 輸出 PDF/Excel 會寫入 `output/`。
- Log 位置：`output/YYYYMMDD_HHMMSS.log`（執行結束後自動開啟）。

## 目錄結構

```
auto-counts-documents-and-product-number/
├── input/                  # 來源 PDF 放這裡（不遞迴子資料夾）
├── 印章/removebg/          # 透明印章 PNG
├── template.xlsx           # Excel 明細模板
├── output/                 # 輸出 PDF 與明細 Excel
├── docs/                   # 需求規格與開發文件
├── archive/                # 歷史樣本與校正歸檔
└── src/doc_processor/      # 核心程式碼
```

## 處理流程

### Phase 0：PDF 蓋章

- 依檔名前綴判斷單據類型，自動蓋上對應印章。
- 採購單：承辦人章 + 供應商章（依供商代號）。
- 進貨驗收單：倉管章 + 製單章。
- 請購單、進貨單：製單章。
- **影像自然化**：每頁印章隨機旋轉（-3° ~ +6°）與位移，模擬人工蓋章效果。

### Phase 1：PDF 合併

- 同一 PDF 可能包含多個採購單，會逐頁解析。
- 若同採購單號且頁次顯示多頁（例如 1/2、2/2），會合併為同一張單。
- 缺進貨驗收單或進貨單的採購單組會整組跳過。

### Phase 2：Excel 明細

- 以檔名採購單號為主，並用進貨單內文採購單號做 double check；不一致會跳過。
- 採購單頁判定關鍵字：`採購日期:`、`廠商:`、`承製廠商簽回`。
- 張數：`單據號碼` 出現次數；支數：採購單頁的 `^\d{4}$` 序號數量。

## Log 結論摘要

每次執行結束後，Log 結尾會包含：
- 各階段執行結果統計
- 需補齊的文件/檔案清單
- 下一步行動建議

## 測試

```powershell
uv run pytest tests/ -v
```

## 文件與規格

- [專案開發指南 (AGENTS.md)](./AGENTS.md)
- [領域模型詞彙表 (CONTEXT.md)](./CONTEXT.md)
- [單據重組與蓋章需求規格 (PRD)](./docs/prds/document-processing.md)
- [自動列印規格 (PRD)](./docs/prds/auto-printing.md)

