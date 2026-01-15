"""PDF 文字提取與欄位解析模組"""

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import fitz  # PyMuPDF


class DocType(Enum):
    """單據類型"""
    PURCHASE_ORDER = "採購單"          # 採購單
    PURCHASE_REQUEST = "請購單"        # 請購單
    GOODS_RECEIPT = "進貨單"           # 進貨單
    RECEIPT_INSPECTION = "進貨驗收單"  # 進貨驗收單
    UNKNOWN = "未知"


# 正則表達式（用於獨立行匹配）
REGEX_PURCHASE_ORDER_NO_VALUE = re.compile(r"^1[0-9]{12}$")  # 採購單號值
REGEX_PURCHASE_REQUEST_NO_VALUE = re.compile(r"^1A[0-9]{11}$")  # 請購單號值
REGEX_RECEIPT_INSPECTION_NO_VALUE = re.compile(r"^1[0-9]{12}$")  # 驗收單號值
REGEX_GOODS_RECEIPT_NO_VALUE = re.compile(r"^1[0-9]{12}$")  # 進貨單號值

# 供商資訊正則
REGEX_VENDOR_CODE = re.compile(r"[A-Za-z]+\d+")
REGEX_VENDOR_NAME_CN = re.compile(r"[\u4e00-\u9fff]+")
REGEX_VENDOR_NAME_EN = re.compile(r"[A-Za-z]+")

# 序號正則（用於計算支數）
REGEX_SEQUENCE_NO = re.compile(r"^\d{4}$")
REGEX_PAGE_SEQUENCE = re.compile(r"(\d+)\s*/\s*(\d+)")


@dataclass
class ParsedDocument:
    """解析後的單據資料"""
    path: Path
    doc_type: DocType
    text: str
    page_index: int | None = None  # PDF 頁碼（從 0 開始）
    page_indices: list[int] | None = None  # PDF 頁碼列表
    purchase_order_no: str | None = None  # 採購單號（直接關聯）
    purchase_request_no: str | None = None  # 請購單號（間接關聯）
    goods_receipt_no: str | None = None  # 進貨單號
    receipt_inspection_no: str | None = None  # 驗收單號
    vendor_code: str | None = None  # 供商代號
    vendor_name: str | None = None  # 供商簡稱


def detect_doc_type(filename: str) -> DocType:
    """從檔名判斷單別（注意順序：先判斷較長的）"""
    if filename.startswith("進貨驗收單"):
        return DocType.RECEIPT_INSPECTION
    elif filename.startswith("進貨單"):
        return DocType.GOODS_RECEIPT
    elif filename.startswith("採購單"):
        return DocType.PURCHASE_ORDER
    elif filename.startswith("請購單"):
        return DocType.PURCHASE_REQUEST
    return DocType.UNKNOWN


def extract_text(pdf_path: Path) -> str:
    """從 PDF 提取全部文字"""
    doc = fitz.open(pdf_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def extract_text_by_page(pdf_path: Path) -> list[str]:
    """從 PDF 逐頁提取文字"""
    doc = fitz.open(pdf_path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return pages


def _parse_document_text(
    pdf_path: Path,
    doc_type: DocType,
    text: str,
    page_index: int | None,
) -> ParsedDocument:
    parsed = ParsedDocument(
        path=pdf_path,
        doc_type=doc_type,
        text=text,
        page_index=page_index,
        page_indices=[page_index] if page_index is not None else None,
    )

    if doc_type == DocType.PURCHASE_REQUEST:
        parsed.purchase_request_no = extract_field_value(
            text, "請購單號", REGEX_PURCHASE_REQUEST_NO_VALUE
        )
    elif doc_type == DocType.GOODS_RECEIPT:
        parsed.goods_receipt_no = extract_field_value(
            text, "單據號碼", REGEX_GOODS_RECEIPT_NO_VALUE
        )
        parsed.purchase_order_no = extract_purchase_order_no_from_goods_receipt_text(
            text, parsed.goods_receipt_no
        )
    else:
        parsed.purchase_order_no = extract_field_value(
            text, "採購單號", REGEX_PURCHASE_ORDER_NO_VALUE
        )

    if doc_type == DocType.RECEIPT_INSPECTION:
        parsed.receipt_inspection_no = extract_field_value(
            text, "驗收單號", REGEX_RECEIPT_INSPECTION_NO_VALUE
        )
        parsed.vendor_code, parsed.vendor_name = extract_vendor_info(text)

    if doc_type == DocType.PURCHASE_ORDER:
        parsed.purchase_request_no = extract_field_value(
            text, "請購單號", REGEX_PURCHASE_REQUEST_NO_VALUE
        )

    return parsed


def parse_documents(pdf_path: Path) -> list[ParsedDocument]:
    """解析 PDF 文件（逐頁）"""
    doc_type = detect_doc_type(pdf_path.name)
    if doc_type == DocType.UNKNOWN:
        return []

    pages = extract_text_by_page(pdf_path)
    parsed_pages = []
    page_sequences = []
    for page_index, page_text in enumerate(pages):
        parsed_pages.append(
            _parse_document_text(pdf_path, doc_type, page_text, page_index)
        )
        page_sequences.append(extract_page_sequence(page_text))

    grouped_docs: list[ParsedDocument] = []
    for page_doc in parsed_pages:
        if not grouped_docs:
            grouped_docs.append(page_doc)
            continue

        previous = grouped_docs[-1]
        if _should_merge_consecutive_pages(
            previous,
            page_doc,
            page_sequences,
        ):
            previous.text = f"{previous.text}\n{page_doc.text}"
            if previous.page_indices is None:
                previous.page_indices = []
            if page_doc.page_index is not None:
                previous.page_indices.append(page_doc.page_index)
                previous.page_index = previous.page_indices[0]
            _merge_optional_fields(previous, page_doc)
            continue

        grouped_docs.append(page_doc)

    return grouped_docs


def parse_document(pdf_path: Path) -> ParsedDocument:
    """解析單一 PDF 文件"""
    doc_type = detect_doc_type(pdf_path.name)
    text = extract_text(pdf_path)
    return _parse_document_text(pdf_path, doc_type, text, None)


def _find_marker_indices(lines: list[str], marker: str) -> list[int]:
    """找到所有包含標籤的行索引"""
    return [i for i, line in enumerate(lines) if marker in line]


def _search_value_near_marker(
    lines: list[str],
    marker_idx: int,
    value_regex: re.Pattern,
    exclude: str | None = None,
    first_only: bool = False,
) -> list[str]:
    """在標籤附近搜尋符合格式的值"""
    values: list[str] = []
    search_range = range(marker_idx, min(marker_idx + 25, len(lines)))

    for j in search_range:
        line = lines[j].strip()
        if value_regex.match(line):
            if exclude and line == exclude:
                continue
            values.append(line)
            if first_only:
                break

    return values


def extract_field_value(
    text: str,
    marker: str,
    value_regex: re.Pattern,
    exclude: str | None = None,
) -> str | None:
    """
    從文字中抽取欄位值

    PDF 文字提取時，標籤和值可能在不同行，因此：
    1. 先找到標籤所在行
    2. 在標籤附近幾行尋找符合格式的值
    """
    lines = text.split("\n")

    for marker_idx in _find_marker_indices(lines, marker):
        values = _search_value_near_marker(
            lines, marker_idx, value_regex, exclude, first_only=True
        )
        if values:
            return values[0]

    return None


def extract_field_values(
    text: str,
    marker: str,
    value_regex: re.Pattern,
) -> list[str]:
    """從文字中抽取欄位可能值（不去重）"""
    lines = text.split("\n")
    values: list[str] = []

    for marker_idx in _find_marker_indices(lines, marker):
        values.extend(_search_value_near_marker(lines, marker_idx, value_regex))

    return values


def extract_field_values_first(
    text: str,
    marker: str,
    value_regex: re.Pattern,
) -> list[str]:
    """從文字中抽取欄位值（每個標籤只取第一個）"""
    lines = text.split("\n")
    values: list[str] = []

    for marker_idx in _find_marker_indices(lines, marker):
        marker_values = _search_value_near_marker(
            lines, marker_idx, value_regex, first_only=True
        )
        values.extend(marker_values)

    return values


def extract_page_sequence(text: str) -> tuple[int, int] | None:
    """抽取頁碼序號（例如 1 / 2）"""
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if "頁" in line and "次" in line:
            for j in range(i, min(i + 5, len(lines))):
                match = REGEX_PAGE_SEQUENCE.search(lines[j])
                if match:
                    return int(match.group(1)), int(match.group(2))
    return None


def _get_group_key(doc: ParsedDocument) -> str | None:
    if doc.doc_type == DocType.PURCHASE_REQUEST:
        return doc.purchase_request_no
    return doc.purchase_order_no


def _should_merge_consecutive_pages(
    previous: ParsedDocument,
    current: ParsedDocument,
    page_sequences: list[tuple[int, int] | None],
) -> bool:
    if previous.doc_type != current.doc_type:
        return False

    previous_key = _get_group_key(previous)
    current_key = _get_group_key(current)
    if not previous_key or not current_key or previous_key != current_key:
        return False

    if previous.page_indices:
        previous_last_index = previous.page_indices[-1]
    else:
        previous_last_index = previous.page_index

    if previous_last_index is None or current.page_index is None:
        return False

    previous_seq = page_sequences[previous_last_index]
    current_seq = page_sequences[current.page_index]
    if not previous_seq or not current_seq:
        return False

    previous_page_no, previous_total = previous_seq
    current_page_no, current_total = current_seq
    if previous_total <= 1 or current_total <= 1:
        return False

    return (
        previous_total == current_total
        and current_page_no == previous_page_no + 1
    )


def _merge_optional_fields(target: ParsedDocument, source: ParsedDocument) -> None:
    if not target.goods_receipt_no:
        target.goods_receipt_no = source.goods_receipt_no
    if not target.receipt_inspection_no:
        target.receipt_inspection_no = source.receipt_inspection_no
    if not target.vendor_code:
        target.vendor_code = source.vendor_code
    if not target.vendor_name:
        target.vendor_name = source.vendor_name


def extract_purchase_order_no_from_goods_receipt_text(
    text: str,
    goods_receipt_no: str | None = None,
) -> str | None:
    """從進貨單文字抽取採購單號"""
    candidates = extract_field_values(
        text, "採購單號", REGEX_PURCHASE_ORDER_NO_VALUE
    )
    if not candidates:
        return None

    goods_receipt_candidates = set(
        extract_field_values_first(text, "單據號碼", REGEX_GOODS_RECEIPT_NO_VALUE)
    )
    if goods_receipt_no:
        goods_receipt_candidates.add(goods_receipt_no)

    for candidate in candidates:
        if candidate not in goods_receipt_candidates:
            return candidate

    if len(goods_receipt_candidates) == 1:
        return next(iter(goods_receipt_candidates))

    return None


def extract_purchase_order_nos_from_goods_receipt_pages(
    pages: list[str],
) -> set[str]:
    """
    從進貨單頁面抽取採購單號。

    以「單據號碼」定位進貨單頁，避免非進貨單頁面的採購單號干擾。
    """
    purchase_order_nos: set[str] = set()
    for page_text in pages:
        if "單據號碼" not in page_text:
            continue
        purchase_order_no = extract_purchase_order_no_from_goods_receipt_text(
            page_text
        )
        if purchase_order_no:
            purchase_order_nos.add(purchase_order_no)
    return purchase_order_nos


def extract_vendor_info(text: str) -> tuple[str | None, str | None]:
    """從進貨驗收單文字中抽取供商代號和供商簡稱"""
    lines = text.split("\n")
    vendor_code = None
    vendor_name = None

    # 尋找供商代號和供商簡稱的位置
    code_marker_idx = None
    name_marker_idx = None

    for i, line in enumerate(lines):
        if "供商代號" in line:
            code_marker_idx = i
        if "供商簡稱" in line:
            name_marker_idx = i

    # 在標記位置附近尋找符合格式的值
    if code_marker_idx is not None:
        # 在標記後的幾行尋找供商代號（字母+數字）
        for j in range(code_marker_idx, min(code_marker_idx + 10, len(lines))):
            line = lines[j].strip()
            match = REGEX_VENDOR_CODE.fullmatch(line)
            if match:
                vendor_code = match.group(0)
                break

    if name_marker_idx is not None:
        # 在標記後的幾行尋找供商簡稱（純中文或純英文）
        for j in range(name_marker_idx, min(name_marker_idx + 15, len(lines))):
            line = lines[j].strip()
            # 跳過已知的非供商名稱欄位
            if any(keyword in line for keyword in ["供商", "聯絡", "備註", "採購", "傳真", "電話", "驗收"]):
                continue
            # 嘗試匹配純中文
            if REGEX_VENDOR_NAME_CN.fullmatch(line) and len(line) >= 2:
                vendor_name = line
                break
            # 嘗試匹配純英文
            if REGEX_VENDOR_NAME_EN.fullmatch(line) and len(line) >= 2:
                vendor_name = line
                break

    return vendor_code, vendor_name


def merge_pdfs(documents: list[ParsedDocument], output_path: Path) -> None:
    """合併多個 PDF 為一份"""
    merged = fitz.open()
    for document in documents:
        doc = fitz.open(document.path)
        if document.page_indices:
            for page_index in document.page_indices:
                merged.insert_pdf(
                    doc,
                    from_page=page_index,
                    to_page=page_index,
                )
        elif document.page_index is not None:
            merged.insert_pdf(
                doc,
                from_page=document.page_index,
                to_page=document.page_index,
            )
        else:
            merged.insert_pdf(doc)
        doc.close()
    merged.save(output_path)
    merged.close()


def count_document_numbers(text: str) -> int:
    """計算「單據號碼」出現的次數（張數）"""
    return text.count("單據號碼")


def count_sequence_numbers(text: str) -> int:
    """計算序號數量（支數）：獨立行的 4 位數字"""
    lines = text.split("\n")
    return sum(1 for line in lines if REGEX_SEQUENCE_NO.match(line.strip()))


def find_purchase_order_page(pages: list[str]) -> str | None:
    """找到採購單頁面（含「採購日期:」的頁面）"""
    keywords = ["採購日期:", "廠商:", "承製廠商簽回"]
    for page_text in pages:
        if any(keyword in page_text for keyword in keywords):
            return page_text
    return None


def extract_purchase_order_no_from_filename(filename: str) -> str | None:
    """從檔名抽取採購單號（格式：{採購單號}-{供商代號}-{供商簡稱}.pdf）"""
    parts = filename.replace(".pdf", "").split("-")
    if len(parts) >= 1:
        # 第一部分應該是採購單號
        candidate = parts[0]
        if re.match(r"1[0-9]{12}$", candidate):
            return candidate
    return None
