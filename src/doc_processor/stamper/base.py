"""蓋章基礎功能模組"""

from dataclasses import dataclass
from pathlib import Path

import fitz
from PIL import Image


@dataclass
class StampConfig:
    """印章配置"""

    x: float  # 左上角 x 座標 (pt)
    y: float  # 左上角 y 座標 (pt)
    target_width: float  # 目標寬度 (pt)
    target_height: float  # 目標高度 (pt)


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
