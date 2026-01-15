# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 專案概述

PDF 採購單據批次重組與 Excel 明細產生器。將當天所有 PDF 單據依採購單號分組合併，並自動填入 Excel 明細。

## 專案地圖

```mermaid
flowchart LR
    root[auto-counts-documents-and-product-number]
    root --> input[input/]
    root --> output[output/]
    root --> PRD[PRD.md]
    root --> AGENTS[AGENTS.md]
    root --> template[template.xlsx]

    input --> |當天採購單據| PDFs[*.pdf]
    output --> |Phase1 合併結果| merged[{採購單號}-{供商代號}-{供商簡稱}.pdf]
    output --> |Phase2 明細| excel[{採購單號}-單據明細.xlsx]
```

## 技術棧

- **入口**：PowerShell 7 (`run.ps1`)
- **核心**：Python + uv 套件管理
- **環境**：Windows 11 25H2
- **編碼**：UTF-8 with BOM（腳本檔）

## 開發指令

```powershell
# 預定入口（尚待實現）
.\run.ps1 phase1    # 批次重組合併 PDF
.\run.ps1 phase2    # 批次產生 Excel 明細
.\run.ps1 all       # 依序執行 Phase1 + Phase2

# 測試（尚待實現）
uv run pytest tests/
```

## 核心處理流程

### Phase 1：PDF 批次合併

1. 掃描 `input/` 所有 `*.pdf`（不含子資料夾）
2. 由**檔名**判斷單別（進貨單、進貨驗收單、採購單、請購單）
3. 由**內文** regex 抽取採購單號進行分組
4. 合併順序固定：進貨單 > 進貨驗收單 > 採購單 > 請購單
5. 輸出：`output/{採購單號}-{供商代號}-{供商簡稱}.pdf`

### Phase 2：Excel 明細生成

1. 掃描 `output/*.pdf`（Phase 1 產出）
2. 內文解析抽取欄位：
   - `{張數}` = count("單據號碼")
   - `{採購單號}` = 從進貨單內文抽取
   - `{支數}` = 從採購單頁計算
3. 填入 `template.xlsx`：B3={支數}、C3={張數}
4. 輸出：`output/{採購單號}-單據明細.xlsx`

## 關鍵正則表達式

```python
採購單號 = r"採購單號:\s?1[0-9]{12}"
請購單號 = r"請購單號:\s?1A[0-9]{11}"
驗收單號 = r"驗收單號:\s?1[0-9]{12}"
進貨單號 = r"單據號碼:\s?1[0-9]{12}"
```

## 供商資訊抽取位置

- `{供商代號}`、`{供商簡稱}`：僅從**進貨驗收單**頁面抽取

## 硬性約束

- **不使用 OCR**：純 PDF 文字層解析
- **不遞迴子資料夾**
- **不設計備援規則**：抓不到資訊即記錄失敗，不做推測
- **不修改 input/**：原始檔案永遠保留
- 合併版執行時，Phase 1 必須完成後才進入 Phase 2

## 測試

- 框架：pytest
- 檔案命名：`test_*.py`
- 固定樣本位置：`tests/fixtures/`（使用脫敏資料）
