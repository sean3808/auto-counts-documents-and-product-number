"""Phase 0：PDF 蓋章階段"""

import io
import random
import re
import shutil
from pathlib import Path

import fitz
from PIL import Image

from .logger import ProcessLogger
from .pdf_parser import BusinessCategory, detect_business_category
from .stamper.base import StampConfig, find_vendor_stamp, scale_image_to_fit
from .stamper.goods_receipt import (
    DEFAULT_CREATOR_STAMP as GR_CREATOR_STAMP,
)
from .stamper.goods_receipt import (
    STAMP_CONFIG_CREATOR as GR_STAMP_CONFIG,
)
from .stamper.purchase_order import (
    DEFAULT_HANDLER_STAMP as PO_HANDLER_STAMP,
)
from .stamper.purchase_order import (
    STAMP_CONFIG_HANDLER as PO_HANDLER_CONFIG,
)
from .stamper.purchase_order import (
    VendorStampConfigError,
    get_vendor_stamp_config,
)
from .stamper.purchase_requisition import (
    DEFAULT_CREATOR_STAMP as PR_CREATOR_STAMP,
)
from .stamper.purchase_requisition import (
    STAMP_CONFIG_CREATOR as PR_STAMP_CONFIG,
)
from .stamper.receiving import (
    DEFAULT_CREATOR_STAMP as RCV_CREATOR_STAMP,
)
from .stamper.receiving import (
    DEFAULT_INSPECTION_STAMP as RCV_INSPECTION_STAMP,
)
from .stamper.receiving import (
    DEFAULT_WAREHOUSE_STAMP as RCV_WAREHOUSE_STAMP,
)
from .stamper.receiving import (
    STAMP_CONFIG_CREATOR as RCV_CREATOR_CONFIG,
)
from .stamper.receiving import (
    STAMP_CONFIG_INSPECTION as RCV_INSPECTION_CONFIG,
)
from .stamper.receiving import (
    STAMP_CONFIG_WAREHOUSE as RCV_WAREHOUSE_CONFIG,
)

# 供商代號正則
REGEX_VENDOR_CODE = r"[A-Z]{2}\d{3}"

# === 自然化設定 ===
# 旋轉角度範圍（整數，度）
# PIL rotate: 正值=逆時針，負值=順時針
ROTATION_MIN_DEGREES = -3
ROTATION_MAX_DEGREES = 3

# 位移範圍（pt，1pt ≈ 0.35mm，對稱微抖動）
OFFSET_X_MIN = -4
OFFSET_X_MAX = 4
OFFSET_Y_MIN = -3
OFFSET_Y_MAX = 3


def run_phase0(
    input_dir: Path,
    output_dir: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
    is_continuation: bool = False,
) -> int:
    """
    Phase 0：掃描 input，對採購單和進貨驗收單蓋章。

    Args:
        input_dir: 輸入資料夾（原始 PDF）
        output_dir: 輸出資料夾（已蓋章 PDF）
        stamps_dir: 印章資料夾
        logger: 日誌記錄器
        is_continuation: 是否為接續模式（用於 all 命令）

    Returns:
        0=成功, 1=部分失敗, 2=完全失敗
    """
    if is_continuation:
        logger.continue_phase("phase0")
    else:
        logger.start("phase0")

    # 確保輸出資料夾存在且清空
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    # 檢查印章資料夾
    stamps_available = stamps_dir.exists()
    if not stamps_available:
        logger.info(f"印章資料夾不存在: {stamps_dir}，將跳過蓋章直接複製")

    # 掃描 input
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info("input 資料夾無 PDF 檔案")
        return logger.finish("Phase 0")

    logger.info(f"找到 {len(pdf_files)} 個 PDF 檔案")

    for pdf_path in pdf_files:
        try:
            output_path = output_dir / pdf_path.name
            filename = pdf_path.name

            # 無印章資料夾時，所有檔案直接複製
            if not stamps_available:
                shutil.copy(pdf_path, output_path)
                logger.ok(f"複製: {filename}")
            elif filename.startswith("採購單~"):
                _process_purchase_order(pdf_path, output_path, stamps_dir, logger)
                logger.ok(f"採購單蓋章: {filename}")
            elif filename.startswith("進貨驗收單~"):
                _process_receiving(pdf_path, output_path, stamps_dir, logger)
                logger.ok(f"進貨驗收單蓋章: {filename}")
            elif filename.startswith("請購單~"):
                _process_single_stamp_document(
                    pdf_path, output_path, stamps_dir, logger,
                    PR_CREATOR_STAMP, PR_STAMP_CONFIG
                )
                logger.ok(f"請購單蓋章: {filename}")
            elif filename.startswith("進貨單~"):
                _process_single_stamp_document(
                    pdf_path, output_path, stamps_dir, logger,
                    GR_CREATOR_STAMP, GR_STAMP_CONFIG
                )
                logger.ok(f"進貨單蓋章: {filename}")
            else:
                # 其他檔案：直接複製
                shutil.copy(pdf_path, output_path)
                logger.ok(f"複製: {filename}")

        except Exception as e:
            logger.error(f"PDF: {pdf_path.name}", str(e))

    return logger.finish("Phase 0")


def _process_purchase_order(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
) -> None:
    """處理採購單：逐頁蓋章。"""
    handler_stamp_path = stamps_dir / PO_HANDLER_STAMP
    handler_exists = handler_stamp_path.exists()

    with fitz.open(input_path) as doc:
        page_count = len(doc)
        for page_idx, page in enumerate(doc):
            text = page.get_text()
            stamps: list[tuple[Path, StampConfig]] = []

            if handler_exists:
                stamps.append((handler_stamp_path, PO_HANDLER_CONFIG))

            vendor_match = re.search(REGEX_VENDOR_CODE, text)
            if vendor_match:
                vendor_code = vendor_match.group()
                vendor_stamp_path = find_vendor_stamp(vendor_code, stamps_dir)
                if vendor_stamp_path:
                    try:
                        vendor_config = get_vendor_stamp_config(vendor_code)
                        if vendor_config:
                            stamps.append((vendor_stamp_path, vendor_config))
                    except VendorStampConfigError as e:
                        logger.error(
                            f"{input_path.name} 第 {page_idx + 1} 頁",
                            str(e).split("\n")[0],
                        )
                else:
                    logger.info(
                        f"{input_path.name} 第 {page_idx + 1} 頁: "
                        f"找不到供應商章 {vendor_code}"
                    )
            else:
                logger.info(
                    f"{input_path.name} 第 {page_idx + 1} 頁: 無法解析供商代號"
                )

            _apply_stamps_to_page(page, stamps)

        doc.save(output_path)

    logger.detail(f"已處理 {page_count} 頁")


def _process_receiving(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
) -> None:
    """處理進貨驗收單：每頁辨識業務類別並蓋章。"""
    with fitz.open(input_path) as doc:
        page_count = len(doc)
        for page in doc:
            text = page.get_text()
            category = detect_business_category(text)

            stamps: list[tuple[Path, StampConfig]] = []
            if category == BusinessCategory.TEXTILE:
                # 紡織類：進料檢驗章 + 製單章（嚴格排除倉管章）
                stamp_candidates = [
                    (stamps_dir / RCV_INSPECTION_STAMP, RCV_INSPECTION_CONFIG),
                    (stamps_dir / RCV_CREATOR_STAMP, RCV_CREATOR_CONFIG),
                ]
            else:
                # 染料類：倉管章 + 製單章
                stamp_candidates = [
                    (stamps_dir / RCV_WAREHOUSE_STAMP, RCV_WAREHOUSE_CONFIG),
                    (stamps_dir / RCV_CREATOR_STAMP, RCV_CREATOR_CONFIG),
                ]

            for stamp_path, config in stamp_candidates:
                if stamp_path.exists():
                    stamps.append((stamp_path, config))
                else:
                    logger.info(f"找不到印章: {stamp_path.name}")

            _apply_stamps_to_page(page, stamps)

        doc.save(output_path)

    logger.detail(f"已處理 {page_count} 頁")


def _apply_stamps_to_page(
    page: fitz.Page,
    stamps: list[tuple[Path, StampConfig]],
) -> None:
    """將印章列表套用到指定頁面（含隨機旋轉與位移）。"""
    for stamp_path, config in stamps:
        with Image.open(stamp_path) as img:
            # 確保 RGBA 模式
            if img.mode != "RGBA":
                img = img.convert("RGBA")

            # 隨機旋轉
            angle = random.randint(ROTATION_MIN_DEGREES, ROTATION_MAX_DEGREES)
            if angle != 0:
                img = img.rotate(angle, expand=True, fillcolor=(0, 0, 0, 0))

            # 縮放（使用旋轉後的尺寸）
            new_w, new_h = scale_image_to_fit(
                img.width, img.height, config.target_width, config.target_height
            )

            # 隨機位移
            offset_x = random.randint(OFFSET_X_MIN, OFFSET_X_MAX)
            offset_y = random.randint(OFFSET_Y_MIN, OFFSET_Y_MAX)

            # 計算最終位置
            x = config.x + offset_x
            y = config.y + offset_y

            # 轉為 bytes 並插入
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            rect = fitz.Rect(x, y, x + new_w, y + new_h)
            page.insert_image(rect, stream=buf.getvalue())


def _process_single_stamp_document(
    input_path: Path,
    output_path: Path,
    stamps_dir: Path,
    logger: ProcessLogger,
    stamp_filename: str,
    stamp_config: StampConfig,
) -> None:
    """處理單一印章文件（請購單、進貨單等）：每頁蓋章。"""
    stamp_path = stamps_dir / stamp_filename
    stamps: list[tuple[Path, StampConfig]] = []

    if stamp_path.exists():
        stamps.append((stamp_path, stamp_config))
    else:
        logger.info(f"找不到印章: {stamp_filename}")

    with fitz.open(input_path) as doc:
        page_count = len(doc)
        for page in doc:
            _apply_stamps_to_page(page, stamps)
        doc.save(output_path)

    logger.detail(f"已處理 {page_count} 頁")
