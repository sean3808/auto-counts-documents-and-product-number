"""採購單蓋章模組"""

import logging
from pathlib import Path

from .base import (
    StampConfig,
    StampsConfig,
    find_vendor_stamp,
    get_target_pt,
    load_stamps_config,
    stamp_pdf,
)

logger = logging.getLogger(__name__)

# 採購單印章配置（座標從範本 PDF 取得）
STAMP_CONFIG_HANDLER = StampConfig(
    x=342.8,
    y=736.7,
    target_width=32.1,
    target_height=17.3,
)

# 供應商印章位置（座標固定，尺寸從 YAML 配置讀取）
VENDOR_STAMP_X = 382.7
VENDOR_STAMP_Y = 612.6

# 預設印章檔名
DEFAULT_HANDLER_STAMP = "雅萍.png"

# 快取配置（避免重複讀取 YAML）
_stamps_config: StampsConfig | None = None


def get_stamps_config() -> StampsConfig:
    """取得印章配置（帶快取）"""
    global _stamps_config
    if _stamps_config is None:
        _stamps_config = load_stamps_config()
    return _stamps_config


def get_vendor_stamp_config(vendor_code: str) -> StampConfig | None:
    """
    取得供應商印章配置。

    Args:
        vendor_code: 供商代號

    Returns:
        StampConfig 或 None（若未配置）
    """
    config = get_stamps_config()
    vendor_code_upper = vendor_code.upper()

    if vendor_code_upper not in config.vendors:
        return None

    vendor_size = config.vendors[vendor_code_upper]
    target_width, target_height = get_target_pt(
        vendor_size.width_cm,
        vendor_size.height_cm,
        config.print_scale,
    )

    return StampConfig(
        x=VENDOR_STAMP_X,
        y=VENDOR_STAMP_Y,
        target_width=target_width,
        target_height=target_height,
    )


class VendorStampConfigError(Exception):
    """供應商印章配置錯誤"""


def stamp_purchase_order(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    vendor_code: str | None = None,
    handler_stamp_name: str = DEFAULT_HANDLER_STAMP,
    remove_background: bool = True,
) -> None:
    """
    在採購單 PDF 上蓋章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps_dir: 印章資料夾路徑
        vendor_code: 供商代號（用於查找供應商章），None 則不蓋供應商章
        handler_stamp_name: 承辦人印章檔名
        remove_background: 是否自動去除印章白色背景（預設 True）

    Raises:
        VendorStampConfigError: 供應商印章存在但未設定尺寸配置
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
            vendor_config = get_vendor_stamp_config(vendor_code)
            if vendor_config is None:
                error_msg = (
                    f"供應商 {vendor_code.upper()} 未設定印章尺寸\n"
                    f"請在 config/stamps.yaml 中新增：\n\n"
                    f"  {vendor_code.upper()}:\n"
                    f"    width_cm: ???   # 請實測後填入\n"
                    f"    height_cm: ???\n"
                )
                logger.error(error_msg)
                raise VendorStampConfigError(error_msg)

            stamps.append((vendor_stamp_path, vendor_config))

    if stamps:
        stamp_pdf(input_path, output_path, stamps, remove_background=remove_background)
    else:
        # 無印章時直接複製
        import shutil

        shutil.copy(input_path, output_path)
