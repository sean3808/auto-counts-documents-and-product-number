"""蓋章基礎功能模組"""

import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import fitz
import numpy as np
import yaml
from PIL import Image

# 常數：1 cm = 28.35 pt (72 pt/inch ÷ 2.54 cm/inch)
CM_TO_PT = 28.35


@dataclass
class VendorStampSize:
    """供應商印章期望列印尺寸 (cm)"""

    width_cm: float
    height_cm: float


@dataclass
class StampsConfig:
    """印章配置（從 YAML 讀取）"""

    print_scale: float
    vendors: dict[str, VendorStampSize] = field(default_factory=dict)


def load_stamps_config(config_path: Path | None = None) -> StampsConfig:
    """
    讀取印章尺寸配置檔。

    Args:
        config_path: 配置檔路徑，預設為專案根目錄的 config/stamps.yaml

    Returns:
        StampsConfig 物件
    """
    if config_path is None:
        # 預設路徑：專案根目錄/config/stamps.yaml
        config_path = Path(__file__).parent.parent.parent.parent / "config" / "stamps.yaml"

    if not config_path.exists():
        raise FileNotFoundError(f"找不到印章配置檔：{config_path}")

    with open(config_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    print_scale = data.get("print_scale", 1.0)
    vendors_data = data.get("vendors", {})

    vendors: dict[str, VendorStampSize] = {}
    for vendor_code, size_data in vendors_data.items():
        vendors[vendor_code.upper()] = VendorStampSize(
            width_cm=size_data["width_cm"],
            height_cm=size_data["height_cm"],
        )

    return StampsConfig(print_scale=print_scale, vendors=vendors)


def get_target_pt(
    width_cm: float, height_cm: float, print_scale: float
) -> tuple[float, float]:
    """
    從期望列印尺寸 (cm) 計算所需的 PDF 目標框尺寸 (pt)。

    考慮列印環境的縮放比例進行補償。

    Args:
        width_cm: 期望列印寬度 (cm)
        height_cm: 期望列印高度 (cm)
        print_scale: 列印縮放比例（如 0.97 表示列印會縮小到 97%）

    Returns:
        (target_width_pt, target_height_pt) 目標框尺寸
    """
    target_width_pt = width_cm / print_scale * CM_TO_PT
    target_height_pt = height_cm / print_scale * CM_TO_PT
    return target_width_pt, target_height_pt


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


def remove_white_background(img: Image.Image, threshold: int = 240) -> Image.Image:
    """
    將圖片的白色（或接近白色）背景轉換為透明。

    Args:
        img: PIL Image 物件
        threshold: 白色閾值（0-255），像素 RGB 值都大於此值時視為白色

    Returns:
        帶有透明背景的 RGBA 圖片
    """
    # 轉換為 RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # 轉換為 numpy array 進行處理
    data = np.array(img)

    # 找出接近白色的像素（R, G, B 都大於 threshold）
    r, g, b, a = data[:, :, 0], data[:, :, 1], data[:, :, 2], data[:, :, 3]
    white_mask = (r > threshold) & (g > threshold) & (b > threshold)

    # 將白色像素的 alpha 設為 0（透明）
    data[:, :, 3] = np.where(white_mask, 0, a)

    return Image.fromarray(data)


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
    remove_background: bool = False,
) -> None:
    """
    在 PDF 指定頁面上蓋印章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps: 印章列表，每個元素為 (印章圖片路徑, StampConfig)
        page_index: 要蓋章的頁面索引（預設第一頁）
        remove_background: 是否自動去除白色背景
    """
    doc = fitz.open(input_path)
    page = doc[page_index]

    for stamp_path, config in stamps:
        # 讀取印章圖片
        with Image.open(stamp_path) as img:
            orig_width, orig_height = img.size

            if remove_background:
                # 去除白色背景
                img = remove_white_background(img)
                # 將處理後的圖片轉為 bytes
                img_buffer = io.BytesIO()
                img.save(img_buffer, format="PNG")
                img_data = img_buffer.getvalue()
            else:
                img_data = None

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
        if img_data:
            page.insert_image(rect, stream=img_data)
        else:
            page.insert_image(rect, filename=str(stamp_path))

    doc.save(output_path)
    doc.close()
