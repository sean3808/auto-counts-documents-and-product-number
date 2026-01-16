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
        stamp_pdf(input_path, output_path, stamps, remove_background=remove_background)
    else:
        # 無印章時直接複製
        import shutil
        shutil.copy(input_path, output_path)
