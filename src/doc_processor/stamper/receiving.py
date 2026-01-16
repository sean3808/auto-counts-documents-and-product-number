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
    remove_background: bool = True,
) -> None:
    """
    在進貨驗收單 PDF 上蓋章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps_dir: 印章資料夾路徑
        warehouse_stamp_name: 倉管人員印章檔名
        creator_stamp_name: 製單人員印章檔名
        remove_background: 是否自動去除印章白色背景（預設 True）
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
        stamp_pdf(input_path, output_path, stamps, remove_background=remove_background)
    else:
        # 無印章時直接複製
        import shutil
        shutil.copy(input_path, output_path)
