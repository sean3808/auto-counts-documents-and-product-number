"""進貨驗收單蓋章模組"""

import re
import shutil
from pathlib import Path

import fitz

from .base import StampConfig, stamp_pdf

# 進貨驗收單印章配置（座標從範本 PDF 取得）
STAMP_CONFIG_WAREHOUSE = StampConfig(
    x=176.1,
    y=743.3,
    target_width=28.0,
    target_height=17.0,
)

STAMP_CONFIG_CREATOR = StampConfig(
    x=508.2,
    y=743.8,
    target_width=32.1,
    target_height=17.3,
)

# 紡織類進貨驗收單進料檢驗章基準配置與防呆邊界常數
INSPECTION_BASE_X = 40.5
INSPECTION_BASE_Y = 270.4
INSPECTION_MAX_Y = 563.3
INSPECTION_CLEARANCE_PT = 20.0
INSPECTION_TARGET_WIDTH = 221.4
INSPECTION_TARGET_HEIGHT = 166.7

# 紡織類進貨驗收單進料檢驗章配置（原圖免去背）
STAMP_CONFIG_INSPECTION = StampConfig(
    x=INSPECTION_BASE_X,
    y=INSPECTION_BASE_Y,
    target_width=INSPECTION_TARGET_WIDTH,
    target_height=INSPECTION_TARGET_HEIGHT,
    remove_background=False,
)

# 預設印章檔名
DEFAULT_WAREHOUSE_STAMP = "簡銘佑.png"
DEFAULT_TEXTILE_WAREHOUSE_STAMP = "莊宛恬.png"
DEFAULT_CREATOR_STAMP = "雅萍.png"
DEFAULT_INSPECTION_STAMP = "紡織進料檢.png"


def calculate_inspection_stamp_y(page: fitz.Page) -> float:
    """
    依進貨驗收單當頁原生文字層動態計算進料檢驗章的垂直座標 y。

    規則：
    - 探測品項序號（0001, 0002...）、備註行（註:對方品名-）以及「以下空白」之最大底緣 y 座標
    - 單頁 1~2 項品項時，進料檢驗章維持於基準座標 (y=270.4 pt)
    - 單頁超過 2 項品項時，進料檢驗章依內容底緣動態向下順推（target_y = max(270.4, content_bottom_y + 20.0)）
    - 安全上限防呆：最高不超過 y=563.3 pt，保證底緣在 730 pt 之前且不遮蔽底部簽核欄 (y=735.5 pt)
    """
    item_numbers: set[str] = set()
    bottom_coords: list[float] = []

    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        block_bbox = block.get("bbox", (0, 0, 0, 0))
        for line in block.get("lines", []):
            bbox = line.get("bbox")
            if not bbox:
                continue
            y0, y1 = bbox[1], bbox[3]
            # 明細品項位在表頭下方 (~150) 且在簽核欄上方 (~735)
            if y0 < 150.0 or y0 >= 735.0:
                continue

            line_text = "".join(span.get("text", "") for span in line.get("spans", [])).strip()
            if not line_text:
                continue

            # 1. 探測品項序號（如 0001, 0002...，排除小數點後零如 .0000）
            seq_matches = [
                m for m in re.findall(r"(?<![.\d])0\d{3}(?![.\d])", line_text)
                if m != "0000"
            ]
            if not seq_matches and re.match(r"^\d{4}$", line_text) and line_text != "0000":
                seq_matches = [line_text]

            matched = False
            if seq_matches:
                item_numbers.update(seq_matches)
                matched = True
            elif (
                "註:對方品名" in line_text
                or "註：對方品名" in line_text
                or line_text.startswith(("註:", "註："))
            ):
                # 2. 探測備註行（註:對方品名-）
                matched = True
            elif "以下空白" in line_text:
                # 3. 探測「以下空白」
                matched = True

            if matched:
                bottom_coords.extend([y1, block_bbox[3]])

    item_count = len(item_numbers)
    if item_count <= 2:
        return INSPECTION_BASE_Y

    content_bottom_y = max(bottom_coords) if bottom_coords else INSPECTION_BASE_Y
    target_y = max(INSPECTION_BASE_Y, content_bottom_y + INSPECTION_CLEARANCE_PT)
    return min(INSPECTION_MAX_Y, target_y)


def get_inspection_stamp_config(page: fitz.Page) -> StampConfig:
    """取得特定頁面之進料檢驗章配置（含動態計算之 y 座標）。"""
    y = calculate_inspection_stamp_y(page)
    return StampConfig(
        x=INSPECTION_BASE_X,
        y=y,
        target_width=INSPECTION_TARGET_WIDTH,
        target_height=INSPECTION_TARGET_HEIGHT,
        remove_background=False,
    )


def stamp_receiving(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    warehouse_stamp_name: str = DEFAULT_WAREHOUSE_STAMP,
    creator_stamp_name: str = DEFAULT_CREATOR_STAMP,
    inspection_stamp_name: str = DEFAULT_INSPECTION_STAMP,
    textile_warehouse_stamp_name: str = DEFAULT_TEXTILE_WAREHOUSE_STAMP,
    remove_background: bool = True,
    is_textile: bool | None = None,
) -> None:
    """
    在進貨驗收單 PDF 上蓋章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps_dir: 印章資料夾路徑
        warehouse_stamp_name: 染料類倉管人員印章檔名
        creator_stamp_name: 製單人員印章檔名
        inspection_stamp_name: 進料檢驗印章檔名
        textile_warehouse_stamp_name: 紡織類倉管人員印章檔名
        remove_background: 是否自動去除印章白色背景（預設 True；進料檢驗章原圖免去背）
        is_textile: 是否為紡織類單據。若為 None 則自動依文字層判定
    """
    if is_textile is None:
        from ..pdf_parser import (
            BusinessCategory,
            detect_business_category,
            extract_text,
        )

        text = extract_text(input_path)
        is_textile = detect_business_category(text) == BusinessCategory.TEXTILE

    stamps: list[tuple[Path, StampConfig]] = []

    if is_textile:
        # 紡織類：進料檢驗章（動態自適應垂直座標）
        inspection_stamp_path = stamps_dir / inspection_stamp_name
        if inspection_stamp_path.exists():
            with fitz.open(input_path) as doc:
                first_page = doc[0] if len(doc) > 0 else None
                insp_config = (
                    get_inspection_stamp_config(first_page)
                    if first_page is not None
                    else STAMP_CONFIG_INSPECTION
                )
            stamps.append((inspection_stamp_path, insp_config))
        warehouse_stamp_path = stamps_dir / textile_warehouse_stamp_name
    else:
        # 染料類：簡銘佑倉管章
        warehouse_stamp_path = stamps_dir / warehouse_stamp_name

    # 倉管人員章（染料類為簡銘佑，紡織類為莊宛恬）
    if warehouse_stamp_path.exists():
        stamps.append((warehouse_stamp_path, STAMP_CONFIG_WAREHOUSE))

    # 製單人員章（雅萍）
    creator_stamp_path = stamps_dir / creator_stamp_name
    if creator_stamp_path.exists():
        stamps.append((creator_stamp_path, STAMP_CONFIG_CREATOR))

    if not stamps:
        shutil.copy(input_path, output_path)
        return

    stamp_pdf(input_path, output_path, stamps, remove_background=remove_background)
