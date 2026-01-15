"""Phase 1：PDF 批次合併邏輯"""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from .logger import ProcessLogger
from .pdf_parser import (
    DocType,
    ParsedDocument,
    detect_doc_type,
    merge_pdfs,
    parse_documents,
)


# 單據類型排序順序
DOC_TYPE_ORDER = {
    DocType.GOODS_RECEIPT: 0,       # 進貨單
    DocType.RECEIPT_INSPECTION: 1,  # 進貨驗收單
    DocType.PURCHASE_ORDER: 2,      # 採購單
    DocType.PURCHASE_REQUEST: 3,    # 請購單
}


@dataclass
class DocumentGroup:
    """同一採購單號的單據組"""
    purchase_order_no: str
    goods_receipts: list[ParsedDocument] = field(default_factory=list)  # 進貨單
    receipt_inspections: list[ParsedDocument] = field(default_factory=list)  # 進貨驗收單
    purchase_orders: list[ParsedDocument] = field(default_factory=list)  # 採購單
    purchase_requests: list[ParsedDocument] = field(default_factory=list)  # 請購單

    def add_document(self, doc: ParsedDocument) -> None:
        """將單據加入對應的列表"""
        if doc.doc_type == DocType.GOODS_RECEIPT:
            self.goods_receipts.append(doc)
        elif doc.doc_type == DocType.RECEIPT_INSPECTION:
            self.receipt_inspections.append(doc)
        elif doc.doc_type == DocType.PURCHASE_ORDER:
            self.purchase_orders.append(doc)
        elif doc.doc_type == DocType.PURCHASE_REQUEST:
            self.purchase_requests.append(doc)

    def get_sorted_documents(self) -> list[ParsedDocument]:
        """取得排序後的 PDF 列表"""
        # 進貨單：依單據號碼升序
        sorted_receipts = sorted(
            self.goods_receipts,
            key=lambda d: (
                d.goods_receipt_no or "",
                d.page_index if d.page_index is not None else -1,
                d.path.name,
            )
        )
        # 進貨驗收單：依驗收單號升序
        sorted_inspections = sorted(
            self.receipt_inspections,
            key=lambda d: (
                d.receipt_inspection_no or "",
                d.page_index if d.page_index is not None else -1,
                d.path.name,
            )
        )
        sorted_orders = sorted(
            self.purchase_orders,
            key=lambda d: (
                d.page_index if d.page_index is not None else -1,
                d.path.name,
            )
        )
        sorted_requests = sorted(
            self.purchase_requests,
            key=lambda d: (
                d.page_index if d.page_index is not None else -1,
                d.path.name,
            )
        )
        all_docs = (
            sorted_receipts +
            sorted_inspections +
            sorted_orders +
            sorted_requests
        )
        return all_docs

    def get_vendor_info(self) -> tuple[str | None, str | None]:
        """從進貨驗收單取得供商資訊"""
        for doc in self.receipt_inspections:
            if doc.vendor_code and doc.vendor_name:
                return doc.vendor_code, doc.vendor_name
        # 只有 vendor_code 的情況
        for doc in self.receipt_inspections:
            if doc.vendor_code:
                return doc.vendor_code, doc.vendor_name
        return None, None

    def get_stats(self) -> dict[str, int]:
        """取得各類型單據數量統計"""
        return {
            "進貨單": len(self.goods_receipts),
            "進貨驗收單": len(self.receipt_inspections),
            "採購單": len(self.purchase_orders),
            "請購單": len(self.purchase_requests),
        }


def run_phase1(input_dir: Path, output_dir: Path, logger: ProcessLogger) -> int:
    """
    執行 Phase 1：掃描 input/，依採購單號合併 PDF 至 output/

    Returns:
        退出碼：0=成功, 1=部分失敗, 2=完全失敗
    """
    logger.start("phase1")

    # 1. 掃描 input/ 所有 *.pdf（不遞迴）
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        logger.info(f"掃描 {input_dir}/ 找到 0 個 PDF 檔案")
        return logger.finish("Phase 1")

    logger.info(f"掃描 {input_dir}/ 找到 {len(pdf_files)} 個 PDF 檔案")

    # 2. 解析所有 PDF
    parsed_docs: list[ParsedDocument] = []
    unknown_docs: list[Path] = []

    for pdf_path in pdf_files:
        doc_type = detect_doc_type(pdf_path.name)
        if doc_type == DocType.UNKNOWN:
            unknown_docs.append(pdf_path)
            continue

        try:
            docs = parse_documents(pdf_path)
        except Exception as e:
            logger.error(f"PDF: {pdf_path.name}", f"解析失敗: {e}")
            continue

        parsed_docs.extend(docs)

    # 統計各類型數量
    type_counts = defaultdict(int)
    for doc in parsed_docs:
        type_counts[doc.doc_type.value] += 1

    type_stats = ", ".join(f"{t} x{c}" for t, c in type_counts.items())
    logger.info(f"識別單據: {type_stats}")

    if unknown_docs:
        for path in unknown_docs:
            logger.skip(f"無法識別: {path.name}", "檔名不符合任何單別格式")

    # 3. 建立請購單號 → 採購單號對照表（從採購單抽取）
    request_to_order: dict[str, str] = {}
    for doc in parsed_docs:
        if doc.doc_type == DocType.PURCHASE_ORDER:
            if doc.purchase_request_no and doc.purchase_order_no:
                request_to_order[doc.purchase_request_no] = doc.purchase_order_no

    # 4. 依採購單號分組
    groups: dict[str, DocumentGroup] = {}

    for doc in parsed_docs:
        # 決定此單據屬於哪個採購單號
        if doc.doc_type == DocType.PURCHASE_REQUEST:
            # 請購單：透過對照表間接關聯
            if doc.purchase_request_no and doc.purchase_request_no in request_to_order:
                po_no = request_to_order[doc.purchase_request_no]
            else:
                logger.skip(
                    f"請購單: {doc.path.name}",
                    f"找不到對應的採購單（請購單號: {doc.purchase_request_no}）"
                )
                continue
        else:
            # 其他單據：直接關聯
            po_no = doc.purchase_order_no
            if not po_no:
                logger.skip(f"{doc.doc_type.value}: {doc.path.name}", "找不到採購單號")
                continue

        # 加入分組
        if po_no not in groups:
            groups[po_no] = DocumentGroup(purchase_order_no=po_no)
        groups[po_no].add_document(doc)

    logger.info(f"分組結果: {len(groups)} 個採購單組")

    # 5. 對每組進行合併
    for po_no, group in groups.items():
        logger.info(f"處理採購單組: {po_no}")
        stats = group.get_stats()
        for doc_type, count in stats.items():
            logger.detail(f"{doc_type}: {count} 張")

        # 檢查是否有進貨驗收單（必要的供商資訊來源）
        if not group.receipt_inspections:
            logger.error(f"採購單組: {po_no}", "沒有進貨驗收單，無法取得供商資訊")
            continue

        # 取得供商資訊
        vendor_code, vendor_name = group.get_vendor_info()
        if not vendor_code:
            logger.error(f"採購單組: {po_no}", "找不到供商代號（進貨驗收單中無匹配 [A-Za-z]+\\d+）")
            continue
        if not vendor_name:
            logger.error(f"採購單組: {po_no}", "找不到供商簡稱")
            continue

        # 取得排序後的 PDF
        documents = group.get_sorted_documents()
        if not documents:
            logger.error(f"採購單組: {po_no}", "沒有可合併的 PDF")
            continue

        # 輸出檔名
        output_filename = f"{po_no}-{vendor_code}-{vendor_name}.pdf"
        output_path = output_dir / output_filename

        # 合併 PDF
        try:
            merge_pdfs(documents, output_path)
            logger.ok(f"輸出: {output_filename}")
        except Exception as e:
            logger.error(f"採購單組: {po_no}", f"PDF 合併失敗: {e}")

    return logger.finish("Phase 1")
