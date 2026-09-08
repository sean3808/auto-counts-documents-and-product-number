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
    x=508.2,
    y=743.8,
    target_width=32.1,
    target_height=17.3,
)

# 紡織類進貨驗收單進料檢驗章配置（原圖免去背）
STAMP_CONFIG_INSPECTION = StampConfig(
    x=40.5,
    y=270.4,
    target_width=221.4,
    target_height=166.7,
    remove_background=False,
)

# 預設印章檔名
DEFAULT_WAREHOUSE_STAMP = "簡銘佑.png"
DEFAULT_CREATOR_STAMP = "雅萍.png"
DEFAULT_INSPECTION_STAMP = "紡織進料檢.png"


def stamp_receiving(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    warehouse_stamp_name: str = DEFAULT_WAREHOUSE_STAMP,
    creator_stamp_name: str = DEFAULT_CREATOR_STAMP,
    inspection_stamp_name: str = DEFAULT_INSPECTION_STAMP,
    remove_background: bool = True,
    is_textile: bool | None = None,
) -> None:
    """
    在進貨驗收單 PDF 上蓋章。

    Args:
        input_path: 輸入 PDF 路徑
        output_path: 輸出 PDF 路徑
        stamps_dir: 印章資料夾路徑
        warehouse_stamp_name: 倉管人員印章檔名
        creator_stamp_name: 製單人員印章檔名
        inspection_stamp_name: 進料檢驗印章檔名
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
        # 紡織類：進料檢驗章 + 製單人員章（嚴格排除倉管人員章）
        inspection_stamp_path = stamps_dir / inspection_stamp_name
        if inspection_stamp_path.exists():
            stamps.append((inspection_stamp_path, STAMP_CONFIG_INSPECTION))

        creator_stamp_path = stamps_dir / creator_stamp_name
        if creator_stamp_path.exists():
            stamps.append((creator_stamp_path, STAMP_CONFIG_CREATOR))
    else:
        # 染料類：倉管人員章 + 製單人員章
        warehouse_stamp_path = stamps_dir / warehouse_stamp_name
        if warehouse_stamp_path.exists():
            stamps.append((warehouse_stamp_path, STAMP_CONFIG_WAREHOUSE))

        creator_stamp_path = stamps_dir / creator_stamp_name
        if creator_stamp_path.exists():
            stamps.append((creator_stamp_path, STAMP_CONFIG_CREATOR))

    if stamps:
        stamp_pdf(input_path, output_path, stamps, remove_background=remove_background)
    else:
        # 無印章時直接複製
        import shutil

        shutil.copy(input_path, output_path)
