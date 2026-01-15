"""Phase 2：Excel 明細生成邏輯"""

from pathlib import Path

from .excel_writer import write_summary
from .logger import ProcessLogger
from .pdf_parser import (
    count_document_numbers,
    count_sequence_numbers,
    extract_purchase_order_nos_from_goods_receipt_pages,
    extract_purchase_order_no_from_filename,
    extract_text,
    extract_text_by_page,
    find_purchase_order_page,
)


def run_phase2(
    output_dir: Path,
    template_path: Path,
    logger: ProcessLogger,
    is_continuation: bool = False,
) -> int:
    """
    執行 Phase 2：掃描 output/ PDF，產生 Excel 明細

    Args:
        output_dir: 輸出資料夾路徑
        template_path: Excel 模板路徑
        logger: ProcessLogger 實例
        is_continuation: 是否為接續 Phase 1 的執行（用於 all 命令）

    Returns:
        退出碼：0=成功, 1=部分失敗, 2=完全失敗
    """
    if is_continuation:
        logger.continue_phase("phase2")
    else:
        logger.start("phase2")

    # 檢查模板是否存在
    if not template_path.exists():
        logger.error("Phase 2", f"找不到模板檔案: {template_path}")
        return logger.finish("Phase 2")

    # 1. 掃描 output/*.pdf（排除非 Phase 1 產出的檔案）
    pdf_files = [
        f for f in output_dir.glob("*.pdf")
        if "-" in f.stem  # Phase 1 輸出格式：{採購單號}-{供商代號}-{供商簡稱}.pdf
    ]

    if not pdf_files:
        logger.info(f"掃描 {output_dir}/ 找到 0 個 PDF 檔案")
        return logger.finish("Phase 2")

    logger.info(f"掃描 {output_dir}/ 找到 {len(pdf_files)} 個 PDF 檔案")

    # 2. 對每份 PDF 處理
    for pdf_path in pdf_files:
        logger.info(f"處理: {pdf_path.name}")

        try:
            # a. 從檔名抽取採購單號
            purchase_order_no = extract_purchase_order_no_from_filename(
                pdf_path.name
            )
            if not purchase_order_no:
                logger.error(f"PDF: {pdf_path.name}", "無法從檔名抽取採購單號")
                continue

            # b. 提取全部文字並計算張數
            full_text = extract_text(pdf_path)
            sheet_count = count_document_numbers(full_text)

            if sheet_count == 0:
                logger.error(f"PDF: {pdf_path.name}", "張數為 0（找不到「單據號碼」）")
                continue

            # c. 從進貨單頁抽取採購單號，與檔名 double check
            pages = extract_text_by_page(pdf_path)
            purchase_order_nos = extract_purchase_order_nos_from_goods_receipt_pages(
                pages
            )
            if not purchase_order_nos:
                logger.error(
                    f"PDF: {pdf_path.name}",
                    "進貨單頁找不到採購單號",
                )
                continue
            if len(purchase_order_nos) > 1:
                logger.error(
                    f"PDF: {pdf_path.name}",
                    f"進貨單頁出現多個採購單號: {sorted(purchase_order_nos)}",
                )
                continue
            purchase_order_no_in_receipt = next(iter(purchase_order_nos))
            if purchase_order_no_in_receipt != purchase_order_no:
                logger.error(
                    f"PDF: {pdf_path.name}",
                    "採購單號不一致（檔名與進貨單內文不符）",
                )
                continue

            # d. 找到採購單頁並計算支數
            purchase_order_page = find_purchase_order_page(pages)

            if not purchase_order_page:
                logger.error(
                    f"PDF: {pdf_path.name}", "找不到採購單頁（無「採購日期:」）"
                )
                continue

            quantity = count_sequence_numbers(purchase_order_page)

            if quantity == 0:
                logger.error(f"PDF: {pdf_path.name}", "支數為 0（採購單頁找不到序號）")
                continue

            logger.detail(f"張數: {sheet_count}")
            logger.detail(f"支數: {quantity}")

            # e. 產生 Excel
            output_excel = output_dir / f"{purchase_order_no}-單據明細.xlsx"

            try:
                write_summary(template_path, output_excel, quantity, sheet_count)
                logger.ok(f"輸出: {output_excel.name}")
            except Exception as e:
                logger.error(f"PDF: {pdf_path.name}", f"Excel 寫入失敗: {e}")
        except Exception as e:
            logger.error(f"PDF: {pdf_path.name}", f"處理失敗: {e}")

    return logger.finish("Phase 2")
