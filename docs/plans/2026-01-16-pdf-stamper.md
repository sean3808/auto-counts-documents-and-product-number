# PDF 自動蓋章功能實作計畫

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在採購單和進貨驗收單 PDF 上自動蓋上對應的印章（個人章 + 供應商大章）

**Architecture:** 使用 PyMuPDF (fitz) 在 PDF 頁面的絕對座標位置插入印章圖片。個人章採固定對應（雅萍、簡銘佑），供應商大章從 PDF 抽取供商代號後比對印章資料夾。印章圖片依類型等比例縮放至目標尺寸。

**Tech Stack:** Python 3.13, PyMuPDF (fitz), Pillow, openpyxl, pathlib

---

## 需求規格摘要

### 印章類型與對應

| 單據類型 | 印章位置 | 印章來源 |
|---------|---------|---------|
| 採購單 | 承辦人 | 固定：`雅萍.png` |
| 採購單 | 承製廠商簽回 | 依供商代號：`{供商代號}.png` |
| 進貨驗收單 | 倉管人員 | 固定：`簡銘佑.png` |
| 進貨驗收單 | 製單人員 | 固定：`雅萍.png` |

### 供應商對照表

檔案：`new/業旺供應商對照表.xlsx`

| 欄位 | 內容 |
|------|------|
| A 欄 | 供應商代碼 (CH058, TW111, ...) |
| B 欄 | 供應商名稱 |

**印章檔案命名規則**：直接用供商代碼，如 `TW111.png`、`CH058.png`

### 座標規格（從範本 PDF 取得）

**採購單** (頁面 596 x 842 pt):
- 承辦人：(335.6, 729.8)，目標尺寸 30 x 17 pt
- 承製廠商簽回：(382.7, 612.6)，目標尺寸 130 x 95 pt

**進貨驗收單** (頁面 612 x 791 pt):
- 倉管人員：(176.1, 743.3)，目標尺寸 28 x 17 pt
- 製單人員：(498.7, 737.9)，目標尺寸 32 x 17 pt

### 印章尺寸處理

- **個人章**：等比例縮放，以高度 17pt 為準
- **供應商大章**：等比例縮放，置入 130 x 95 pt 框內

---

## Task 1: 建立 stamper 模組基礎結構

**Files:**
- Create: `src/doc_processor/stamper/__init__.py`
- Create: `src/doc_processor/stamper/base.py`
- Test: `tests/test_stamper_base.py`

### Step 1: 建立 stamper 目錄

Run:
```powershell
pwsh -Command "New-Item -ItemType Directory -Path 'src/doc_processor/stamper' -Force"
```

### Step 2: 建立 `__init__.py`

Create `src/doc_processor/stamper/__init__.py`:
```python
"""PDF 蓋章模組"""

from .base import StampConfig, find_vendor_stamp, scale_image_to_fit

__all__ = ["StampConfig", "find_vendor_stamp", "scale_image_to_fit"]
```

### Step 3: 寫失敗測試 - StampConfig dataclass

Create `tests/test_stamper_base.py`:
```python
"""stamper.base 模組測試"""

from pathlib import Path

import pytest

from doc_processor.stamper.base import StampConfig, find_vendor_stamp, scale_image_to_fit


class TestStampConfig:
    """StampConfig dataclass 測試"""

    def test_stamp_config_creation(self):
        """測試建立 StampConfig"""
        config = StampConfig(
            x=100.0,
            y=200.0,
            target_width=30.0,
            target_height=17.0,
        )
        assert config.x == 100.0
        assert config.y == 200.0
        assert config.target_width == 30.0
        assert config.target_height == 17.0
```

### Step 4: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestStampConfig::test_stamp_config_creation -v
```
Expected: FAIL with `ModuleNotFoundError: No module named 'doc_processor.stamper'`

### Step 5: 實作 StampConfig

Create `src/doc_processor/stamper/base.py`:
```python
"""蓋章基礎功能模組"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class StampConfig:
    """印章配置"""

    x: float  # 左上角 x 座標 (pt)
    y: float  # 左上角 y 座標 (pt)
    target_width: float  # 目標寬度 (pt)
    target_height: float  # 目標高度 (pt)
```

### Step 6: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestStampConfig::test_stamp_config_creation -v
```
Expected: PASS

### Step 7: Commit

```powershell
git add src/doc_processor/stamper/ tests/test_stamper_base.py
git commit -m "$(cat <<'EOF'
feat(stamper): add StampConfig dataclass

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: 實作 scale_image_to_fit 函式

**Files:**
- Modify: `src/doc_processor/stamper/base.py`
- Test: `tests/test_stamper_base.py`

### Step 1: 寫失敗測試 - scale_image_to_fit

Append to `tests/test_stamper_base.py`:
```python
class TestScaleImageToFit:
    """scale_image_to_fit 函式測試"""

    def test_scale_wider_image(self):
        """測試較寬的圖片（以寬度為準縮放）"""
        # 原始 200x100，目標框 100x100 → 縮放為 100x50
        new_w, new_h = scale_image_to_fit(200, 100, 100, 100)
        assert new_w == 100.0
        assert new_h == 50.0

    def test_scale_taller_image(self):
        """測試較高的圖片（以高度為準縮放）"""
        # 原始 100x200，目標框 100x100 → 縮放為 50x100
        new_w, new_h = scale_image_to_fit(100, 200, 100, 100)
        assert new_w == 50.0
        assert new_h == 100.0

    def test_scale_same_ratio(self):
        """測試相同比例"""
        # 原始 200x100，目標框 100x50 → 縮放為 100x50
        new_w, new_h = scale_image_to_fit(200, 100, 100, 50)
        assert new_w == 100.0
        assert new_h == 50.0

    def test_scale_smaller_image(self):
        """測試已經小於目標的圖片（不放大）"""
        # 原始 50x25，目標框 100x100 → 保持 50x25
        new_w, new_h = scale_image_to_fit(50, 25, 100, 100)
        assert new_w == 50.0
        assert new_h == 25.0
```

### Step 2: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestScaleImageToFit -v
```
Expected: FAIL with `ImportError` or `AttributeError`

### Step 3: 實作 scale_image_to_fit

Add to `src/doc_processor/stamper/base.py`:
```python
def scale_image_to_fit(
    orig_width: float,
    orig_height: float,
    target_width: float,
    target_height: float,
) -> tuple[float, float]:
    """
    計算等比例縮放後的尺寸，使圖片置入目標框內。

    若原始尺寸已小於目標，則不放大。

    Args:
        orig_width: 原始寬度
        orig_height: 原始高度
        target_width: 目標框寬度
        target_height: 目標框高度

    Returns:
        (new_width, new_height) 縮放後的尺寸
    """
    if orig_width <= target_width and orig_height <= target_height:
        return orig_width, orig_height

    width_ratio = target_width / orig_width
    height_ratio = target_height / orig_height
    scale = min(width_ratio, height_ratio)

    return orig_width * scale, orig_height * scale
```

### Step 4: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestScaleImageToFit -v
```
Expected: PASS

### Step 5: Commit

```powershell
git add src/doc_processor/stamper/base.py tests/test_stamper_base.py
git commit -m "$(cat <<'EOF'
feat(stamper): add scale_image_to_fit function

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: 實作 find_vendor_stamp 函式

**Files:**
- Modify: `src/doc_processor/stamper/base.py`
- Test: `tests/test_stamper_base.py`

### Step 1: 寫失敗測試 - find_vendor_stamp

Append to `tests/test_stamper_base.py`:
```python
class TestFindVendorStamp:
    """find_vendor_stamp 函式測試"""

    @pytest.fixture
    def stamps_dir(self, tmp_path: Path) -> Path:
        """建立測試用印章資料夾"""
        stamps = tmp_path / "stamps"
        stamps.mkdir()
        # 建立測試用印章檔案（直接用供商代碼命名）
        for name in ["TW111.png", "TW113.png", "HE058.png"]:
            img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
            img.save(stamps / name)
        return stamps

    def test_find_existing_vendor_stamp(self, stamps_dir: Path):
        """測試找到存在的供應商印章"""
        result = find_vendor_stamp("TW111", stamps_dir)
        assert result is not None
        assert result.name == "TW111.png"

    def test_find_nonexistent_vendor_stamp(self, stamps_dir: Path):
        """測試找不到供應商印章"""
        result = find_vendor_stamp("XX999", stamps_dir)
        assert result is None

    def test_find_vendor_stamp_case_insensitive(self, stamps_dir: Path):
        """測試供商代號不區分大小寫"""
        result = find_vendor_stamp("tw111", stamps_dir)
        assert result is not None
        assert result.stem.upper() == "TW111"

    def test_find_vendor_stamp_jpg(self, stamps_dir: Path):
        """測試 JPG 格式印章"""
        # 建立 JPG 格式印章
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(stamps_dir / "EL037.jpg")

        result = find_vendor_stamp("EL037", stamps_dir)
        assert result is not None
        assert result.name == "EL037.jpg"

    def test_find_vendor_stamp_legacy_format(self, stamps_dir: Path):
        """測試舊格式印章（{代碼}-{名稱}.png）"""
        # 建立舊格式印章
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        img.save(stamps_dir / "CH058-長興隆裕.png")

        result = find_vendor_stamp("CH058", stamps_dir)
        assert result is not None
        assert result.name == "CH058-長興隆裕.png"
```

### Step 2: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestFindVendorStamp -v
```
Expected: FAIL

### Step 3: 實作 find_vendor_stamp

Add to `src/doc_processor/stamper/base.py`:
```python
def find_vendor_stamp(vendor_code: str, stamps_dir: Path) -> Path | None:
    """
    根據供商代號在印章資料夾中尋找對應的印章檔案。

    支持兩種檔案命名格式（優先順序）：
    1. {供商代號}.png / .jpg（新格式）
    2. {供商代號}-{名稱}.png / .jpg（舊格式，向下兼容）

    Args:
        vendor_code: 供商代號（如 TW111）
        stamps_dir: 印章資料夾路徑

    Returns:
        印章檔案路徑，找不到則回傳 None
    """
    if not stamps_dir.exists():
        return None

    vendor_code_upper = vendor_code.upper()

    # 優先找精確匹配：{vendor_code}.ext
    for ext in [".png", ".jpg", ".jpeg"]:
        stamp_path = stamps_dir / f"{vendor_code}{ext}"
        if stamp_path.exists():
            return stamp_path
        stamp_path = stamps_dir / f"{vendor_code_upper}{ext}"
        if stamp_path.exists():
            return stamp_path

    # 次要找前綴匹配：{vendor_code}-*.ext（向下兼容）
    for stamp_file in stamps_dir.iterdir():
        if stamp_file.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
            continue
        stem_upper = stamp_file.stem.upper()
        # 精確匹配 stem
        if stem_upper == vendor_code_upper:
            return stamp_file
        # 前綴匹配（舊格式：TW111-xxx）
        if stem_upper.startswith(f"{vendor_code_upper}-"):
            return stamp_file

    return None
```

### Step 4: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestFindVendorStamp -v
```
Expected: PASS

### Step 5: Commit

```powershell
git add src/doc_processor/stamper/base.py tests/test_stamper_base.py
git commit -m "$(cat <<'EOF'
feat(stamper): add find_vendor_stamp function

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: 實作 stamp_pdf 核心函式

**Files:**
- Modify: `src/doc_processor/stamper/base.py`
- Modify: `src/doc_processor/stamper/__init__.py`
- Test: `tests/test_stamper_base.py`

### Step 1: 寫失敗測試 - stamp_pdf

Append to `tests/test_stamper_base.py`:
```python
import fitz

from doc_processor.stamper.base import stamp_pdf


class TestStampPdf:
    """stamp_pdf 函式測試"""

    @pytest.fixture
    def sample_pdf(self, tmp_path: Path) -> Path:
        """建立測試用 PDF"""
        pdf_path = tmp_path / "test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=595, height=842)
        page.insert_text((100, 100), "Test Document")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def sample_stamp(self, tmp_path: Path) -> Path:
        """建立測試用印章"""
        stamp_path = tmp_path / "stamp.png"
        img = Image.new("RGBA", (100, 50), (255, 0, 0, 128))
        img.save(stamp_path)
        return stamp_path

    def test_stamp_pdf_single_stamp(self, sample_pdf: Path, sample_stamp: Path, tmp_path: Path):
        """測試在 PDF 上蓋單一印章"""
        output_path = tmp_path / "output.pdf"
        stamps = [
            (sample_stamp, StampConfig(x=100, y=700, target_width=50, target_height=25))
        ]

        stamp_pdf(sample_pdf, output_path, stamps)

        assert output_path.exists()
        # 驗證輸出 PDF 有圖片
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 1

    def test_stamp_pdf_multiple_stamps(self, sample_pdf: Path, sample_stamp: Path, tmp_path: Path):
        """測試在 PDF 上蓋多個印章"""
        output_path = tmp_path / "output.pdf"
        stamps = [
            (sample_stamp, StampConfig(x=100, y=700, target_width=50, target_height=25)),
            (sample_stamp, StampConfig(x=300, y=700, target_width=50, target_height=25)),
        ]

        stamp_pdf(sample_pdf, output_path, stamps)

        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 2
```

### Step 2: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestStampPdf -v
```
Expected: FAIL with `ImportError`

### Step 3: 實作 stamp_pdf

Add to `src/doc_processor/stamper/base.py`:
```python
import fitz


def stamp_pdf(
    input_path: Path,
    output_path: Path,
    stamps: list[tuple[Path, StampConfig]],
    page_index: int = 0,
) -> None:
    """
    在 PDF 指定頁面上蓋印章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps: 印章列表，每個元素為 (印章圖片路徑, StampConfig)
        page_index: 要蓋章的頁面索引（預設第一頁）
    """
    doc = fitz.open(input_path)
    page = doc[page_index]

    for stamp_path, config in stamps:
        # 讀取印章圖片尺寸
        with Image.open(stamp_path) as img:
            orig_width, orig_height = img.size

        # 計算縮放後尺寸
        new_width, new_height = scale_image_to_fit(
            orig_width, orig_height, config.target_width, config.target_height
        )

        # 建立插入區域
        rect = fitz.Rect(
            config.x,
            config.y,
            config.x + new_width,
            config.y + new_height,
        )

        # 插入圖片
        page.insert_image(rect, filename=str(stamp_path))

    doc.save(output_path)
    doc.close()
```

### Step 4: 更新 `__init__.py`

Update `src/doc_processor/stamper/__init__.py`:
```python
"""PDF 蓋章模組"""

from .base import StampConfig, find_vendor_stamp, scale_image_to_fit, stamp_pdf

__all__ = ["StampConfig", "find_vendor_stamp", "scale_image_to_fit", "stamp_pdf"]
```

### Step 5: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_base.py::TestStampPdf -v
```
Expected: PASS

### Step 6: Commit

```powershell
git add src/doc_processor/stamper/ tests/test_stamper_base.py
git commit -m "$(cat <<'EOF'
feat(stamper): add stamp_pdf function

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: 實作採購單蓋章模組

**Files:**
- Create: `src/doc_processor/stamper/purchase_order.py`
- Modify: `src/doc_processor/stamper/__init__.py`
- Test: `tests/test_stamper_purchase_order.py`

### Step 1: 寫失敗測試

Create `tests/test_stamper_purchase_order.py`:
```python
"""採購單蓋章模組測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.stamper.purchase_order import (
    STAMP_CONFIG_HANDLER,
    STAMP_CONFIG_VENDOR,
    stamp_purchase_order,
)


class TestPurchaseOrderStampConfigs:
    """採購單印章配置測試"""

    def test_handler_stamp_config(self):
        """測試承辦人印章配置"""
        assert STAMP_CONFIG_HANDLER.x == pytest.approx(335.6, rel=0.1)
        assert STAMP_CONFIG_HANDLER.y == pytest.approx(729.8, rel=0.1)

    def test_vendor_stamp_config(self):
        """測試承製廠商印章配置"""
        assert STAMP_CONFIG_VENDOR.x == pytest.approx(382.7, rel=0.1)
        assert STAMP_CONFIG_VENDOR.y == pytest.approx(612.6, rel=0.1)
```

### Step 2: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_purchase_order.py::TestPurchaseOrderStampConfigs -v
```
Expected: FAIL with `ModuleNotFoundError`

### Step 3: 實作採購單配置

Create `src/doc_processor/stamper/purchase_order.py`:
```python
"""採購單蓋章模組"""

from pathlib import Path

from .base import StampConfig, find_vendor_stamp, stamp_pdf

# 採購單印章配置（座標從範本 PDF 取得）
STAMP_CONFIG_HANDLER = StampConfig(
    x=335.6,
    y=729.8,
    target_width=30.0,
    target_height=17.0,
)

STAMP_CONFIG_VENDOR = StampConfig(
    x=382.7,
    y=612.6,
    target_width=130.0,
    target_height=95.0,
)

# 預設印章檔名
DEFAULT_HANDLER_STAMP = "雅萍.png"
```

### Step 4: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_purchase_order.py::TestPurchaseOrderStampConfigs -v
```
Expected: PASS

### Step 5: 寫失敗測試 - stamp_purchase_order 函式

Append to `tests/test_stamper_purchase_order.py`:
```python
class TestStampPurchaseOrder:
    """stamp_purchase_order 函式測試"""

    @pytest.fixture
    def sample_pdf(self, tmp_path: Path) -> Path:
        """建立測試用採購單 PDF"""
        pdf_path = tmp_path / "採購單~1011501020005.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "供商代號：TW111")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def stamps_dir(self, tmp_path: Path) -> Path:
        """建立測試用印章資料夾"""
        stamps = tmp_path / "stamps"
        stamps.mkdir()
        # 建立個人章
        handler_stamp = Image.new("RGBA", (106, 56), (255, 0, 0, 128))
        handler_stamp.save(stamps / "雅萍.png")
        # 建立供應商章（直接用供商代碼命名）
        vendor_stamp = Image.new("RGBA", (395, 308), (0, 255, 0, 128))
        vendor_stamp.save(stamps / "TW111.png")
        return stamps

    def test_stamp_purchase_order_with_vendor(
        self, sample_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試採購單蓋章（含供應商章）"""
        output_path = tmp_path / "output.pdf"

        stamp_purchase_order(
            input_path=sample_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            vendor_code="TW111",
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應有 2 個印章：承辦人 + 供應商
        assert len(images) == 2

    def test_stamp_purchase_order_without_vendor(
        self, sample_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試採購單蓋章（無供應商章）"""
        output_path = tmp_path / "output.pdf"

        stamp_purchase_order(
            input_path=sample_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            vendor_code=None,
        )

        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應只有 1 個印章：承辦人
        assert len(images) == 1
```

### Step 6: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_purchase_order.py::TestStampPurchaseOrder -v
```
Expected: FAIL with `ImportError`

### Step 7: 實作 stamp_purchase_order

Add to `src/doc_processor/stamper/purchase_order.py`:
```python
def stamp_purchase_order(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    vendor_code: str | None = None,
    handler_stamp_name: str = DEFAULT_HANDLER_STAMP,
) -> None:
    """
    在採購單 PDF 上蓋章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps_dir: 印章資料夾路徑
        vendor_code: 供商代號（用於查找供應商章），None 則不蓋供應商章
        handler_stamp_name: 承辦人印章檔名
    """
    stamps: list[tuple[Path, StampConfig]] = []

    # 承辦人印章
    handler_stamp_path = stamps_dir / handler_stamp_name
    if handler_stamp_path.exists():
        stamps.append((handler_stamp_path, STAMP_CONFIG_HANDLER))

    # 供應商印章
    if vendor_code:
        vendor_stamp_path = find_vendor_stamp(vendor_code, stamps_dir)
        if vendor_stamp_path:
            stamps.append((vendor_stamp_path, STAMP_CONFIG_VENDOR))

    if stamps:
        stamp_pdf(input_path, output_path, stamps)
    else:
        # 無印章時直接複製
        import shutil
        shutil.copy(input_path, output_path)
```

### Step 8: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_purchase_order.py -v
```
Expected: PASS

### Step 9: Commit

```powershell
git add src/doc_processor/stamper/ tests/test_stamper_purchase_order.py
git commit -m "$(cat <<'EOF'
feat(stamper): add purchase order stamping module

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: 實作進貨驗收單蓋章模組

**Files:**
- Create: `src/doc_processor/stamper/receiving.py`
- Modify: `src/doc_processor/stamper/__init__.py`
- Test: `tests/test_stamper_receiving.py`

### Step 1: 寫失敗測試

Create `tests/test_stamper_receiving.py`:
```python
"""進貨驗收單蓋章模組測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.stamper.receiving import (
    STAMP_CONFIG_WAREHOUSE,
    STAMP_CONFIG_CREATOR,
    stamp_receiving,
)


class TestReceivingStampConfigs:
    """進貨驗收單印章配置測試"""

    def test_warehouse_stamp_config(self):
        """測試倉管人員印章配置"""
        assert STAMP_CONFIG_WAREHOUSE.x == pytest.approx(176.1, rel=0.1)
        assert STAMP_CONFIG_WAREHOUSE.y == pytest.approx(743.3, rel=0.1)

    def test_creator_stamp_config(self):
        """測試製單人員印章配置"""
        assert STAMP_CONFIG_CREATOR.x == pytest.approx(498.7, rel=0.1)
        assert STAMP_CONFIG_CREATOR.y == pytest.approx(737.9, rel=0.1)


class TestStampReceiving:
    """stamp_receiving 函式測試"""

    @pytest.fixture
    def sample_pdf(self, tmp_path: Path) -> Path:
        """建立測試用進貨驗收單 PDF"""
        pdf_path = tmp_path / "進貨驗收單~採單1011501020005.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def stamps_dir(self, tmp_path: Path) -> Path:
        """建立測試用印章資料夾"""
        stamps = tmp_path / "stamps"
        stamps.mkdir()
        # 建立個人章
        warehouse_stamp = Image.new("RGBA", (99, 190), (255, 0, 0, 128))
        warehouse_stamp.save(stamps / "簡銘佑.png")
        creator_stamp = Image.new("RGBA", (106, 56), (0, 255, 0, 128))
        creator_stamp.save(stamps / "雅萍.png")
        return stamps

    def test_stamp_receiving(
        self, sample_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試進貨驗收單蓋章"""
        output_path = tmp_path / "output.pdf"

        stamp_receiving(
            input_path=sample_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應有 2 個印章：倉管人員 + 製單人員
        assert len(images) == 2
```

### Step 2: 執行測試確認失敗

Run:
```powershell
uv run pytest tests/test_stamper_receiving.py -v
```
Expected: FAIL with `ModuleNotFoundError`

### Step 3: 實作進貨驗收單蓋章模組

Create `src/doc_processor/stamper/receiving.py`:
```python
"""進貨驗收單蓋章模組"""

from pathlib import Path

from .base import StampConfig, stamp_pdf

# 進貨驗收單印章配置（座標從範本 PDF 取得）
STAMP_CONFIG_WAREHOUSE = StampConfig(
    x=176.1,
    y=743.3,
    target_width=28.0,
    target_height=17.0,
)

STAMP_CONFIG_CREATOR = StampConfig(
    x=498.7,
    y=737.9,
    target_width=32.0,
    target_height=17.0,
)

# 預設印章檔名
DEFAULT_WAREHOUSE_STAMP = "簡銘佑.png"
DEFAULT_CREATOR_STAMP = "雅萍.png"


def stamp_receiving(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    warehouse_stamp_name: str = DEFAULT_WAREHOUSE_STAMP,
    creator_stamp_name: str = DEFAULT_CREATOR_STAMP,
) -> None:
    """
    在進貨驗收單 PDF 上蓋章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps_dir: 印章資料夾路徑
        warehouse_stamp_name: 倉管人員印章檔名
        creator_stamp_name: 製單人員印章檔名
    """
    stamps: list[tuple[Path, StampConfig]] = []

    # 倉管人員印章
    warehouse_stamp_path = stamps_dir / warehouse_stamp_name
    if warehouse_stamp_path.exists():
        stamps.append((warehouse_stamp_path, STAMP_CONFIG_WAREHOUSE))

    # 製單人員印章
    creator_stamp_path = stamps_dir / creator_stamp_name
    if creator_stamp_path.exists():
        stamps.append((creator_stamp_path, STAMP_CONFIG_CREATOR))

    if stamps:
        stamp_pdf(input_path, output_path, stamps)
    else:
        # 無印章時直接複製
        import shutil
        shutil.copy(input_path, output_path)
```

### Step 4: 執行測試確認通過

Run:
```powershell
uv run pytest tests/test_stamper_receiving.py -v
```
Expected: PASS

### Step 5: 更新 `__init__.py`

Update `src/doc_processor/stamper/__init__.py`:
```python
"""PDF 蓋章模組"""

from .base import StampConfig, find_vendor_stamp, scale_image_to_fit, stamp_pdf
from .purchase_order import stamp_purchase_order
from .receiving import stamp_receiving

__all__ = [
    "StampConfig",
    "find_vendor_stamp",
    "scale_image_to_fit",
    "stamp_pdf",
    "stamp_purchase_order",
    "stamp_receiving",
]
```

### Step 6: Commit

```powershell
git add src/doc_processor/stamper/ tests/test_stamper_receiving.py
git commit -m "$(cat <<'EOF'
feat(stamper): add receiving document stamping module

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: 執行全部測試並驗證

**Files:**
- All test files

### Step 1: 執行全部測試

Run:
```powershell
uv run pytest tests/ -v
```
Expected: All tests PASS

### Step 2: 執行整合測試（使用實際印章資料夾）

Run:
```powershell
uv run python -c "
from pathlib import Path
from doc_processor.stamper import stamp_purchase_order, stamp_receiving

# 測試採購單蓋章
stamp_purchase_order(
    input_path=Path('new/採購單~1011501020005.pdf'),
    output_path=Path('output/test_stamped_purchase_order.pdf'),
    stamps_dir=Path('印章'),
    vendor_code='TW111',
)
print('採購單蓋章完成')

# 測試進貨驗收單蓋章
stamp_receiving(
    input_path=Path('new/進貨驗收單~採單1011501020005.pdf'),
    output_path=Path('output/test_stamped_receiving.pdf'),
    stamps_dir=Path('印章'),
)
print('進貨驗收單蓋章完成')
"
```

### Step 3: 目視檢查輸出 PDF

檢查 `output/test_stamped_purchase_order.pdf` 和 `output/test_stamped_receiving.pdf`，確認印章位置正確。

### Step 4: Commit

```powershell
git add -A
git commit -m "$(cat <<'EOF'
test: verify stamper module integration

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>
EOF
)"
```

---

## 完成檢查清單

- [ ] Task 1: stamper 模組基礎結構
- [ ] Task 2: scale_image_to_fit 函式
- [ ] Task 3: find_vendor_stamp 函式
- [ ] Task 4: stamp_pdf 核心函式
- [ ] Task 5: 採購單蓋章模組
- [ ] Task 6: 進貨驗收單蓋章模組
- [ ] Task 7: 全部測試通過 + 整合驗證
