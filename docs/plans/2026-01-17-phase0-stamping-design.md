# Phase 0 蓋章階段設計文件

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 Phase 1 合併前，對原始 PDF 蓋章，輸出到暫存區供後續流程使用

**Architecture:** Phase 0 掃描 input/ 的 PDF，根據檔名判斷單據類型，對採購單和進貨驗收單蓋章後輸出到 temp/stamped/，進貨單和請購單直接複製。Phase 1 改為讀取 temp/stamped/。

**Tech Stack:** Python 3.13, PyMuPDF (fitz), Pillow, pathlib

---

## 資料流

```
input/                    # 原始單據（不修改）
    ↓ Phase 0: 蓋章
temp/stamped/             # 已蓋章的單據
    ↓ Phase 1: 分組合併
output/*.pdf              # 合併後 PDF
    ↓ Phase 2: Excel
output/*-單據明細.xlsx
```

## 單據處理規則

| 單據類型 | 檔名前綴 | 蓋章內容 | 備註 |
|---------|---------|---------|------|
| 採購單 | `採購單~` | 承辦人章 + 供應商章 | 逐頁解析供商代號 |
| 進貨驗收單 | `進貨驗收單~` | 倉管章 + 製單章 | 每頁蓋章 |
| 進貨單 | `進貨單~` | 不蓋章 | 直接複製 |
| 請購單 | `請購單~` | 不蓋章 | 直接複製 |

## CLI 變更

### 新增參數

```python
parser.add_argument(
    "--stamps",
    type=Path,
    default=Path("./印章/removebg"),
    help="印章資料夾路徑（預設: ./印章/removebg）",
)
```

### 命令擴充

```python
choices=["phase0", "phase1", "phase2", "all"]
```

### all 執行順序

```
phase0 (input → temp/stamped)
   ↓ 失敗碼 2 → 中止
phase1 (temp/stamped → output)
   ↓ 失敗碼 2 → 中止
phase2 (output → Excel)
```

## 錯誤處理

| 情境 | 處理方式 |
|------|---------|
| 印章資料夾不存在 | 警告並跳過蓋章，直接複製 PDF |
| 找不到供應商章 | 只蓋承辦人章，記錄警告 |
| 找不到人名章 | 跳過該印章，記錄警告 |
| PDF 解析失敗 | 跳過該檔案，記錄錯誤 |
| 供商代號解析失敗 | 只蓋承辦人章，記錄警告 |

## 退出碼

| 代碼 | 意義 |
|------|------|
| 0 | 成功 |
| 1 | 部分失敗（有跳過的項目） |
| 2 | 完全失敗 |

---

## Task 1: 建立 phase0.py 基礎結構

**Files:**
- Create: `src/doc_processor/phase0.py`
- Test: `tests/test_phase0.py`

### Step 1: 建立測試檔案

Create `tests/test_phase0.py`:
```python
"""Phase 0 蓋章階段測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.phase0 import run_phase0
from doc_processor.logger import ProcessLogger


class TestRunPhase0:
    """run_phase0 函式測試"""

    @pytest.fixture
    def setup_dirs(self, tmp_path: Path):
        """建立測試用資料夾結構"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "temp" / "stamped"
        stamps_dir = tmp_path / "stamps"
        log_dir = tmp_path / "logs"

        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        stamps_dir.mkdir(parents=True)
        log_dir.mkdir(parents=True)

        # 建立測試用印章
        handler_stamp = Image.new("RGBA", (106, 56), (255, 0, 0, 128))
        handler_stamp.save(stamps_dir / "雅萍.png")

        warehouse_stamp = Image.new("RGBA", (99, 60), (0, 255, 0, 128))
        warehouse_stamp.save(stamps_dir / "簡銘佑.png")

        vendor_stamp = Image.new("RGBA", (200, 150), (0, 0, 255, 128))
        vendor_stamp.save(stamps_dir / "TW111.png")

        return {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "stamps_dir": stamps_dir,
            "log_dir": log_dir,
        }

    @pytest.fixture
    def sample_purchase_order(self, setup_dirs) -> Path:
        """建立測試用採購單 PDF"""
        pdf_path = setup_dirs["input_dir"] / "採購單~test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "TW111")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def sample_receiving(self, setup_dirs) -> Path:
        """建立測試用進貨驗收單 PDF"""
        pdf_path = setup_dirs["input_dir"] / "進貨驗收單~test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_phase0_empty_input(self, setup_dirs):
        """測試空 input 資料夾"""
        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )
        # 空資料夾應回傳成功
        assert result == 0

    def test_phase0_purchase_order(self, setup_dirs, sample_purchase_order):
        """測試採購單蓋章"""
        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )

        assert result == 0
        output_file = setup_dirs["output_dir"] / "採購單~test.pdf"
        assert output_file.exists()

        # 驗證有蓋章
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) >= 1

    def test_phase0_receiving(self, setup_dirs, sample_receiving):
        """測試進貨驗收單蓋章"""
        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )

        assert result == 0
        output_file = setup_dirs["output_dir"] / "進貨驗收單~test.pdf"
        assert output_file.exists()

        # 驗證有蓋章
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 2  # 倉管章 + 製單章
```

### Step 2: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_phase0.py -v
```
Expected: FAIL with `ModuleNotFoundError`

### Step 3: 實作 phase0.py 基礎結構

Create `src/doc_processor/phase0.py`:
```python
"""Phase 0：PDF 蓋章階段"""

import shutil
from pathlib import Path

import fitz

from .logger import ProcessLogger
from .pdf_parser import extract_text_by_page
from .stamper import stamp_purchase_order, stamp_receiving
from .stamper.base import StampConfig, find_vendor_stamp

# 供商代號正則（從 pdf_parser 借用）
REGEX_VENDOR_CODE = r"[A-Z]{2}\d{3}"


def run_phase0(
    input_dir: Path,
    output_dir: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
) -> int:
    """
    Phase 0：掃描 input，對採購單和進貨驗收單蓋章。

    Args:
        input_dir: 輸入資料夾（原始 PDF）
        output_dir: 輸出資料夾（已蓋章 PDF）
        stamps_dir: 印章資料夾
        logger: 日誌記錄器

    Returns:
        0=成功, 1=部分失敗, 2=完全失敗
    """
    logger.info("=== Phase 0: PDF 蓋章 ===")

    # 確保輸出資料夾存在且清空
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # 檢查印章資料夾
    if not stamps_dir.exists():
        logger.warning(f"印章資料夾不存在: {stamps_dir}，將跳過蓋章直接複製")

    # 掃描 input
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info("input 資料夾無 PDF 檔案")
        return 0

    logger.info(f"找到 {len(pdf_files)} 個 PDF 檔案")

    success_count = 0
    fail_count = 0

    for pdf_path in pdf_files:
        try:
            output_path = output_dir / pdf_path.name
            filename = pdf_path.name

            if filename.startswith("採購單~"):
                _process_purchase_order(pdf_path, output_path, stamps_dir, logger)
            elif filename.startswith("進貨驗收單~"):
                _process_receiving(pdf_path, output_path, stamps_dir, logger)
            else:
                # 進貨單、請購單等：直接複製
                shutil.copy(pdf_path, output_path)
                logger.info(f"複製: {filename}")

            success_count += 1

        except Exception as e:
            logger.error(f"處理失敗 {pdf_path.name}: {e}")
            fail_count += 1

    # 統計結果
    logger.info(f"Phase 0 完成: 成功 {success_count}, 失敗 {fail_count}")

    if fail_count == 0:
        return 0
    elif success_count == 0:
        return 2
    else:
        return 1


def _process_purchase_order(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
) -> None:
    """處理採購單：逐頁蓋章"""
    import re

    from .stamper.purchase_order import (
        DEFAULT_HANDLER_STAMP,
        STAMP_CONFIG_HANDLER,
        STAMP_CONFIG_VENDOR,
    )
    from .stamper.base import stamp_pdf, scale_image_to_fit
    from PIL import Image

    doc = fitz.open(input_path)
    page_count = len(doc)

    for page_idx in range(page_count):
        page = doc[page_idx]
        text = page.get_text()

        stamps: list[tuple[Path, StampConfig]] = []

        # 承辦人章
        handler_stamp_path = stamps_dir / DEFAULT_HANDLER_STAMP
        if handler_stamp_path.exists():
            stamps.append((handler_stamp_path, STAMP_CONFIG_HANDLER))

        # 供應商章（從該頁文字解析供商代號）
        vendor_match = re.search(REGEX_VENDOR_CODE, text)
        if vendor_match:
            vendor_code = vendor_match.group()
            vendor_stamp_path = find_vendor_stamp(vendor_code, stamps_dir)
            if vendor_stamp_path:
                stamps.append((vendor_stamp_path, STAMP_CONFIG_VENDOR))
            else:
                logger.warning(f"{input_path.name} 第 {page_idx + 1} 頁: 找不到供應商章 {vendor_code}")
        else:
            logger.warning(f"{input_path.name} 第 {page_idx + 1} 頁: 無法解析供商代號")

        # 蓋章
        for stamp_path, config in stamps:
            with Image.open(stamp_path) as img:
                orig_w, orig_h = img.size
            new_w, new_h = scale_image_to_fit(orig_w, orig_h, config.target_width, config.target_height)
            rect = fitz.Rect(config.x, config.y, config.x + new_w, config.y + new_h)
            page.insert_image(rect, filename=str(stamp_path))

    doc.save(output_path)
    doc.close()
    logger.info(f"採購單蓋章: {input_path.name} ({page_count} 頁)")


def _process_receiving(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
) -> None:
    """處理進貨驗收單：每頁蓋章"""
    from .stamper.receiving import (
        DEFAULT_WAREHOUSE_STAMP,
        DEFAULT_CREATOR_STAMP,
        STAMP_CONFIG_WAREHOUSE,
        STAMP_CONFIG_CREATOR,
    )
    from .stamper.base import scale_image_to_fit
    from PIL import Image

    doc = fitz.open(input_path)
    page_count = len(doc)

    stamps_config = [
        (stamps_dir / DEFAULT_WAREHOUSE_STAMP, STAMP_CONFIG_WAREHOUSE),
        (stamps_dir / DEFAULT_CREATOR_STAMP, STAMP_CONFIG_CREATOR),
    ]

    for page_idx in range(page_count):
        page = doc[page_idx]

        for stamp_path, config in stamps_config:
            if not stamp_path.exists():
                logger.warning(f"找不到印章: {stamp_path.name}")
                continue

            with Image.open(stamp_path) as img:
                orig_w, orig_h = img.size
            new_w, new_h = scale_image_to_fit(orig_w, orig_h, config.target_width, config.target_height)
            rect = fitz.Rect(config.x, config.y, config.x + new_w, config.y + new_h)
            page.insert_image(rect, filename=str(stamp_path))

    doc.save(output_path)
    doc.close()
    logger.info(f"進貨驗收單蓋章: {input_path.name} ({page_count} 頁)")
```

### Step 4: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_phase0.py -v
```
Expected: PASS

### Step 5: Commit

```powershell
git add src/doc_processor/phase0.py tests/test_phase0.py
git commit -m "$(cat <<'EOF'
feat(phase0): add PDF stamping phase

- Add run_phase0() to stamp PDFs before Phase 1
- Purchase orders: stamp each page with handler + vendor stamps
- Receiving docs: stamp each page with warehouse + creator stamps
- Other docs: copy without stamping

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 更新 CLI 整合 Phase 0

**Files:**
- Modify: `src/doc_processor/cli.py`
- Test: `tests/test_cli.py`（如存在）

### Step 1: 更新 cli.py

Modify `src/doc_processor/cli.py`:
```python
"""CLI 入口模組"""

import argparse
import sys
from pathlib import Path

from .logger import ProcessLogger
from .phase0 import run_phase0
from .phase1 import run_phase1
from .phase2 import run_phase2

# 預設暫存資料夾
DEFAULT_TEMP_DIR = Path("./temp/stamped")


def main() -> int:
    """CLI 主入口"""
    parser = argparse.ArgumentParser(
        prog="doc_processor",
        description="採購單關聯單據重組與單據明細產生器",
    )
    parser.add_argument(
        "command",
        choices=["phase0", "phase1", "phase2", "all"],
        help="執行的階段：phase0=蓋章, phase1=合併PDF, phase2=產生Excel, all=依序執行",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("./input"),
        help="輸入資料夾路徑（預設: ./input）",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("./output"),
        help="輸出資料夾路徑（預設: ./output）",
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=Path("./template.xlsx"),
        help="Excel 模板路徑（預設: ./template.xlsx）",
    )
    parser.add_argument(
        "--stamps",
        type=Path,
        default=Path("./印章/removebg"),
        help="印章資料夾路徑（預設: ./印章/removebg）",
    )

    args = parser.parse_args()

    # 確保輸出資料夾存在
    args.output.mkdir(parents=True, exist_ok=True)

    # 建立 logger
    logger = ProcessLogger(args.output)

    # 執行指定的階段
    if args.command == "phase0":
        return run_phase0(args.input, DEFAULT_TEMP_DIR, args.stamps, logger)

    elif args.command == "phase1":
        # Phase 1 單獨執行時，從 input 讀取（向後兼容）
        return run_phase1(args.input, args.output, logger)

    elif args.command == "phase2":
        return run_phase2(args.output, args.template, logger)

    elif args.command == "all":
        # 依序執行 Phase 0 + Phase 1 + Phase 2
        exit_code_0 = run_phase0(args.input, DEFAULT_TEMP_DIR, args.stamps, logger)

        if exit_code_0 == 2:
            return exit_code_0

        # Phase 1 從 temp/stamped 讀取
        exit_code_1 = run_phase1(DEFAULT_TEMP_DIR, args.output, logger)

        if exit_code_1 == 2:
            return max(exit_code_0, exit_code_1)

        exit_code_2 = run_phase2(
            args.output, args.template, logger, is_continuation=True
        )

        return max(exit_code_0, exit_code_1, exit_code_2)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```

### Step 2: 更新 .gitignore 排除 temp/

Append to `.gitignore`:
```
# Phase 0 暫存
temp/
```

### Step 3: 手動測試

Run:
```powershell
# 測試 phase0 單獨執行
uv run python -m doc_processor phase0

# 測試 all 完整流程
uv run python -m doc_processor all
```

### Step 4: Commit

```powershell
git add src/doc_processor/cli.py .gitignore
git commit -m "$(cat <<'EOF'
feat(cli): integrate Phase 0 into CLI

- Add phase0 command for standalone stamping
- Add --stamps parameter (default: ./印章/removebg)
- Update 'all' to run phase0 → phase1 → phase2
- Phase 1 reads from temp/stamped when run via 'all'

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 執行全部測試並驗證

### Step 1: 執行全部測試

Run:
```powershell
uv run pytest tests/ -v
```
Expected: All tests PASS

### Step 2: 整合測試

Run:
```powershell
uv run python -m doc_processor all --stamps "./印章/removebg"
```

### Step 3: 檢查輸出

- 確認 `temp/stamped/` 有蓋章後的 PDF
- 確認 `output/` 有合併後的 PDF
- 確認 `output/*-單據明細.xlsx` 有產生

---

## 完成檢查清單

- [ ] Task 1: phase0.py 基礎結構與測試
- [ ] Task 2: CLI 整合 Phase 0
- [ ] Task 3: 全部測試通過 + 整合驗證
