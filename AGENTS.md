# Repository Guidelines

PDF 採購單據批次自動蓋章（Phase 0）、依採購單號分組合併（Phase 1）、生成 Excel 明細（Phase 2）。

## 1. 處理流程與核心規則 (Pipeline & Domain Rules)

### 資料流管線
```
input/*.pdf (+ 印章/removebg/) ➔ Phase 0 (蓋章) ➔ temp/stamped/ ➔ Phase 1 (分組合併) ➔ output/*.pdf ➔ Phase 2 (Excel明細) ➔ output/*-單據明細.xlsx
```

### 單據對應關係
- 請購單 : 採購單 = 1 : 1
- 採購單 : 進貨單 = 1 : N
- 採購單 : 進貨驗收單 = 1 : N

### 核心處理流程

#### Phase 0：PDF 蓋章
1. 掃描 `input/*.pdf`（不遞迴子目錄），依**檔名前綴**判斷單據類型。
2. 蓋章規則：
   - **採購單**：承辦人章（雅萍）+ 依內文抽取之供商代號蓋對應供應商章。
   - **進貨驗收單**：
     - **染料類**：倉管章（簡銘佑）+ 製單章（雅萍）。
     - **紡織類**：進料檢驗章（紡織進料檢，免去背）+ 製單章（雅萍），不蓋倉管章。
   - **進貨單**：製單章（雅萍）。
   - **請購單**：製單章（雅萍）。
3. **影像自然化**：每頁印章隨機微旋轉（-3° ~ +3°）與隨機對稱微位移（x: -4~+4pt、y: -3~+3pt）。
4. 輸出至 `temp/stamped/{原檔名}`。

#### Phase 1：PDF 分組合併
1. 掃描 `temp/stamped/`，依檔名開頭判斷單別（優先順序：進貨驗收單 > 進貨單 > 採購單 > 請購單）。
2. 依內文採購單號分組（請購單透過採購單號間接關聯）。
3. 多採購單 PDF 逐頁解析；同採購單號跨頁（如頁次 1/2、2/2）合併為同一張單。
4. 合併順序固定：**進貨單 > 進貨驗收單 > 採購單 > 請購單**；同類單據依號碼升序排列。
5. 輸出命名：`output/{採購單號}-{供商代號}-{供商簡稱}.pdf`。

#### Phase 2：Excel 明細生成
1. 掃描 `output/*.pdf`（Phase 1 產物），抽取張數與支數：
   - `{張數}` = 內文中 `"單據號碼"` 出現次數。
   - `{支數}` = 採購單頁（含 `採購日期:`、`廠商:` 或 `承製廠商簽回`）中符合 `^\d{4}$` 的獨立行數量。
2. 載入 `template.xlsx` 填入 B3=`{支數}`、C3=`{張數}`。
3. 輸出命名：`output/{採購單號}-單據明細.xlsx`。

---

## 2. 欄位抽取與約束規範 (Extraction & Constraints)

### 關鍵抽取模式 (Regex)
- **單號抽取**（標籤後獨立行匹配）：
  - 採購單號 / 驗收單號 / 進貨單號（單據號碼）：`1[0-9]{12}`
  - 請購單號：`1A[0-9]{11}`
- **供商資訊**（從進貨驗收單抽取）：
  - 供商代號：`[A-Za-z]+\d+`（採購單蓋章用：`[A-Z]{2}\d{3}`）
  - 供商簡稱：純中文字或純英文字（不含數字）

### 硬性約束與容錯原則 (Strict Constraints)
- **純文字層解析 (No OCR)**：全流程僅抽取 PDF 原生文字層，禁止使用 OCR。
- **零推測/零備援 (Zero Guesswork)**：抓不到資訊時記錄錯誤並跳過該組，禁止使用猜測或備援 heuristic 填補。
- **輸入目錄不可變**：`input/` 嚴格唯讀，禁止就地修改或覆寫。
- **缺單略過**：缺進貨單或進貨驗收單時跳過該組；請購單找不到對應採購單時跳過該請購單。
- **日誌與結論**：所有執行記錄寫入 `output/YYYYMMDD_HHMMSS.log`，日誌結尾產出結論摘要（含統計與缺單補齊建議）。
- **退出碼**：`0`（全部成功）、`1`（部分略過）、`2`（完全失敗）。

---

## 3. 專案架構與模組職責 (Architecture & Modules)

```
auto-counts-documents-and-product-number/
├── run.ps1                 # PowerShell 入口腳本
├── run.bat                 # Windows 批次檔入口（雙擊執行）
├── pyproject.toml          # uv 專案設定
├── template.xlsx           # Excel 模板（B3=支數, C3=張數）
├── CONTEXT.md              # 領域模型詞彙表
├── docs/                   # 專案文件
│   └── prds/               # 需求規格（document-processing.md, auto-printing.md）
├── src/doc_processor/
│   ├── cli.py              # CLI 入口，調度 phase0/phase1/phase2/all
│   ├── phase0.py           # Phase 0：PDF 蓋章與影像自然化
│   ├── phase1.py           # Phase 1：PDF 分組、排序與合併
│   ├── phase2.py           # Phase 2：張數/支數計算與 Excel 明細產出
│   ├── pdf_parser.py       # PDF 文字提取、單別判斷、欄位抽取、PDF 合併
│   ├── excel_writer.py     # Excel 模板載入與數值填入
│   ├── logger.py           # 統一 Log 格式與結論摘要
│   └── stamper/            # 蓋章引擎（座標、縮放、旋轉、供應商印章定位）
├── tests/                  # pytest 測試套件 (tests/fixtures/ 為脫敏樣本)
├── input/                  # 待處理 PDF 來源（gitignore，嚴禁修改）
├── temp/stamped/           # Phase 0 暫存區（gitignore）
├── output/                 # 產出結果與執行日誌（gitignore）
├── archive/                # 歷史樣本與校正資料歸檔（gitignore）
└── 印章/removebg/          # 已去背透明 PNG 印章（gitignore）
```

- **領域模型**：[`CONTEXT.md`](./CONTEXT.md)
- **需求規格**：[`docs/prds/document-processing.md`](./docs/prds/document-processing.md)、[`docs/prds/auto-printing.md`](./docs/prds/auto-printing.md)

---

## 4. 開發與執行指令 (Commands)

```powershell
# PowerShell 入口（預設 all）
.\run.ps1 [phase0 | phase1 | phase2 | all]

# Python CLI 入口
uv run python -m doc_processor [phase0 | phase1 | phase2 | all]
uv run python -m doc_processor all --stamps "./印章/removebg"

# 執行測試（79 個測試案例全數通過）
uv run pytest tests/ -v
uv run pytest tests/test_pdf_parser.py -v

# 環境依賴同步
uv sync --extra dev
```

---

## 5. 編碼與 Windows 平台規範 (Encoding & Platform Guidelines)

- **文字檔編碼**：所有文字檔（特別是 `.py`、`.md`、`.json`、`.yaml` 等）**強制使用 UTF-8 No BOM**。
- **路徑與 I/O**：一律使用 `pathlib.Path` 物件處理路徑；讀寫檔案明確指定 `encoding='utf-8'`（嚴禁 `utf-8-sig`）。
- **中文檔名存取**：優先使用 Glob/原生讀檔工具或 `Path.glob()`，避免在 Shell 中使用非 UTF-8 字串直接拼接中文路徑。
- **PowerShell 執行**：若需輸出中文，於指令開頭指定 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`。
- **印章圖片**：一律使用 `印章/removebg/` 下預先去背之透明 PNG。

---

## 6. 程式碼風格與 Git 規範 (Style & Commit Guidelines)

- **Python**：PEP 8，4 空格縮排，`snake_case` 函式與模組命名，`PascalCase` 類別命名。
- **PowerShell**：`Verb-Noun` 命名。
- **Commit 格式**：Conventional Commits（`feat:`, `fix:`, `docs:`, `refactor:`, `test:`）。
- **Issue 關聯結案**：完工結案一律於 Commit message 中使用 GitHub 規範之 Closing Keywords（如 `closes #123`, `fixes #45`）。
- **資安與脫敏**：禁止提交真實廠商文件或敏感採購資料；`input/`、`temp/`、`output/`、`印章/`、`archive/` 皆在 `.gitignore`；測試檔案僅使用脫敏樣本。

---

## 7. Agent skills

### Issue tracker

GitHub Issues (`sean3808/auto-counts-documents-and-product-number`). See `docs/agents/issue-tracker.md`.

### Triage labels

Canonical five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context (`CONTEXT.md` + `docs/adr/` at repo root). See `docs/agents/domain.md`.

> 復原進行中的工作前，先讀專案根目錄的 `session-continuity.md`（跨-agent session 交接狀態，由 /session-park 維護）。
