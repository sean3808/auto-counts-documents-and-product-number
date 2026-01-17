"""Phase 0：PDF 蓋章階段"""

import re
import shutil
from pathlib import Path

import fitz
from PIL import Image

from .logger import ProcessLogger
from .stamper.base import StampConfig, find_vendor_stamp, scale_image_to_fit

# 供商代號正則
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
    stamps_available = stamps_dir.exists()
    if not stamps_available:
        logger.info(f"印章資料夾不存在: {stamps_dir}，將跳過蓋章直接複製")

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

            # 無印章資料夾時，所有檔案直接複製
            if not stamps_available:
                shutil.copy(pdf_path, output_path)
                logger.info(f"複製: {filename}")
            elif filename.startswith("採購單~"):
                _process_purchase_order(pdf_path, output_path, stamps_dir, logger)
            elif filename.startswith("進貨驗收單~"):
                _process_receiving(pdf_path, output_path, stamps_dir, logger)
            else:
                # 進貨單、請購單等：直接複製
                shutil.copy(pdf_path, output_path)
                logger.info(f"複製: {filename}")

            success_count += 1

        except Exception as e:
            logger.error(f"PDF: {pdf_path.name}", str(e))
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
    from .stamper.purchase_order import (
        DEFAULT_HANDLER_STAMP,
        STAMP_CONFIG_HANDLER,
        STAMP_CONFIG_VENDOR,
    )

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
                logger.info(
                    f"{input_path.name} 第 {page_idx + 1} 頁: 找不到供應商章 {vendor_code}"
                )
        else:
            logger.info(
                f"{input_path.name} 第 {page_idx + 1} 頁: 無法解析供商代號"
            )

        # 蓋章
        for stamp_path, config in stamps:
            with Image.open(stamp_path) as img:
                orig_w, orig_h = img.size
            new_w, new_h = scale_image_to_fit(
                orig_w, orig_h, config.target_width, config.target_height
            )
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
        DEFAULT_CREATOR_STAMP,
        DEFAULT_WAREHOUSE_STAMP,
        STAMP_CONFIG_CREATOR,
        STAMP_CONFIG_WAREHOUSE,
    )

    doc = fitz.open(input_path)
    page_count = len(doc)

    # 預先檢查印章是否存在，避免每頁重複警告
    stamps_config: list[tuple[Path, StampConfig]] = []
    for stamp_path, config in [
        (stamps_dir / DEFAULT_WAREHOUSE_STAMP, STAMP_CONFIG_WAREHOUSE),
        (stamps_dir / DEFAULT_CREATOR_STAMP, STAMP_CONFIG_CREATOR),
    ]:
        if stamp_path.exists():
            stamps_config.append((stamp_path, config))
        else:
            logger.info(f"找不到印章: {stamp_path.name}")

    for page_idx in range(page_count):
        page = doc[page_idx]

        for stamp_path, config in stamps_config:
            with Image.open(stamp_path) as img:
                orig_w, orig_h = img.size
            new_w, new_h = scale_image_to_fit(
                orig_w, orig_h, config.target_width, config.target_height
            )
            rect = fitz.Rect(config.x, config.y, config.x + new_w, config.y + new_h)
            page.insert_image(rect, filename=str(stamp_path))

    doc.save(output_path)
    doc.close()
    logger.info(f"進貨驗收單蓋章: {input_path.name} ({page_count} 頁)")
