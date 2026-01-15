# doc-processor

採購單關聯單據重組與單據明細產生器。將同一採購單的相關 PDF
重新分組合併，並依模板輸出 Excel 明細。

## 需求

- Windows 11
- Python 3.13+
- uv 套件管理器

## 安裝

```powershell
uv sync --extra dev
```

## 使用方式

```powershell
# Phase 1: 合併 PDF
.\run.ps1 phase1

# Phase 2: 產生 Excel 明細
.\run.ps1 phase2

# 一鍵執行
.\run.ps1 all
```

或用 Python 執行：

```powershell
uv run python -m doc_processor phase1
uv run python -m doc_processor phase2
uv run python -m doc_processor all
```

## 輸入與輸出

- 將來源 PDF 放在 `input/`（不遞迴子資料夾）。
- 輸出 PDF/Excel 會寫入 `output/`。
- Log 位置：`output/YYYYMMDD_HHMMSS.log`。

## 行為說明

- 同一 PDF 可能包含多個採購單，會逐頁解析。
- 若同採購單號且頁次顯示多頁（例如 1/2、2/2），會合併為同一張單。
- 缺進貨驗收單或進貨單的採購單組會整組跳過。
- Phase 2 以檔名採購單號為主，並用進貨單內文採購單號做 double check；
  不一致會跳過。
- 採購單頁判定關鍵字：`採購日期:`、`廠商:`、`承製廠商簽回`。
- 張數：`單據號碼` 出現次數；支數：採購單頁的 `^\d{4}$` 序號數量。

## 測試

```powershell
uv run pytest tests/ -v
```
