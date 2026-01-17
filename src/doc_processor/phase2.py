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


def _validate_purchase_order_nos(
    pages: list[str],
    expected_po_no: str,
) -> tuple[bool, str]:
    """
    驗證進貨單頁的採購單號是否與預期一致

    Returns:
        (is_valid, error_message)
    """
    purchase_order_nos = extract_purchase_order_nos_from_goods_receipt_pages(pages)

    if not purchase_order_nos:
        return False, "進貨單頁找不到採購單號"

    if len(purchase_order_nos) > 1:
        return False, f"進貨單頁出現多個採購單號: {sorted(purchase_order_nos)}"

    actual_po_no = next(iter(purchase_order_nos))
    if actual_po_no != expected_po_no:
        return False, "採購單號不一致（檔名與進貨單內文不符）"

    return True, ""


def _process_pdf(
    pdf_path: Path,
    template_path: Path,
    output_dir: Path,
    logger: ProcessLogger,
) -> bool:
    """
    處理單一 PDF 檔案

    Returns:
        True 表示成功，False 表示失敗
    """
    pdf_name = pdf_path.name
    logger.info(f"處理: {pdf_name}")

    purchase_order_no = extract_purchase_order_no_from_filename(pdf_name)
    if not purchase_order_no:
        logger.error(f"PDF: {pdf_name}", "無法從檔名抽取採購單號")
        return False

    full_text = extract_text(pdf_path)
    sheet_count = count_document_numbers(full_text)
    if sheet_count == 0:
        logger.error(f"PDF: {pdf_name}", "張數為 0（找不到「單據號碼」）")
        return False

    pages = extract_text_by_page(pdf_path)

    is_valid, error_msg = _validate_purchase_order_nos(pages, purchase_order_no)
    if not is_valid:
        logger.error(f"PDF: {pdf_name}", error_msg)
        return False

    purchase_order_page = find_purchase_order_page(pages)
    if not purchase_order_page:
        logger.error(f"PDF: {pdf_name}", "找不到採購單頁（無「採購日期:」）")
        return False

    quantity = count_sequence_numbers(purchase_order_page)
    if quantity == 0:
        logger.error(f"PDF: {pdf_name}", "支數為 0（採購單頁找不到序號）")
        return False

    logger.detail(f"張數: {sheet_count}")
    logger.detail(f"支數: {quantity}")

    output_excel = output_dir / f"{purchase_order_no}-單據明細.xlsx"
    try:
        write_summary(template_path, output_excel, quantity, sheet_count)
        logger.ok(f"輸出: {output_excel.name}")
        return True
    except Exception as e:
        logger.error(f"PDF: {pdf_name}", f"Excel 寫入失敗: {e}")
        return False


def run_phase2(
    output_dir: Path,
    template_path: Path,
    logger: ProcessLogger,
    is_continuation: bool = False,
) -> int:
    """
    執行 Phase 2：掃描 output/ PDF，產生 Excel 明細

    Returns:
        退出碼：0=成功, 1=部分失敗, 2=完全失敗
    """
    if is_continuation:
        logger.continue_phase("phase2")
    else:
        logger.start("phase2")

    if not template_path.exists():
        logger.error(
            "Phase 2",
            f"找不到模板檔案: {template_path}",
            suggestion=f"請確認模板檔案存在於指定路徑: {template_path}",
        )
        return logger.finish("Phase 2")

    # Phase 1 輸出格式：{採購單號}-{供商代號}-{供商簡稱}.pdf
    pdf_files = [f for f in output_dir.glob("*.pdf") if "-" in f.stem]

    if not pdf_files:
        logger.info(f"掃描 {output_dir}/ 找到 0 個 PDF 檔案")
        return logger.finish("Phase 2")

    logger.info(f"掃描 {output_dir}/ 找到 {len(pdf_files)} 個 PDF 檔案")

    for pdf_path in pdf_files:
        try:
            _process_pdf(pdf_path, template_path, output_dir, logger)
        except Exception as e:
            logger.error(f"PDF: {pdf_path.name}", f"處理失敗: {e}")

    return logger.finish("Phase 2")
