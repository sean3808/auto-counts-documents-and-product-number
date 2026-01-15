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


@dataclass
class ParsedDocument:
    """解析後的單據資料"""
    path: Path
    doc_type: DocType
    text: str
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


def parse_document(pdf_path: Path) -> ParsedDocument:
    """解析單一 PDF 文件"""
    filename = pdf_path.name
    doc_type = detect_doc_type(filename)
    text = extract_text(pdf_path)

    parsed = ParsedDocument(
        path=pdf_path,
        doc_type=doc_type,
        text=text,
    )

    # 進貨單：先抽取單據號碼（因為需要用來排除）
    if doc_type == DocType.GOODS_RECEIPT:
        parsed.goods_receipt_no = extract_field_value(
            text, "單據號碼", REGEX_GOODS_RECEIPT_NO_VALUE
        )

    # 依單別抽取關聯單號
    if doc_type == DocType.PURCHASE_REQUEST:
        # 請購單：抽取請購單號（間接關聯）
        parsed.purchase_request_no = extract_field_value(
            text, "請購單號", REGEX_PURCHASE_REQUEST_NO_VALUE
        )
    else:
        # 其他單據：抽取採購單號（直接關聯）
        # 對於進貨單，需要排除單據號碼（格式相同）
        exclude_value = parsed.goods_receipt_no if doc_type == DocType.GOODS_RECEIPT else None
        parsed.purchase_order_no = extract_field_value(
            text, "採購單號", REGEX_PURCHASE_ORDER_NO_VALUE, exclude=exclude_value
        )

    # 進貨驗收單：額外抽取驗收單號和供商資訊
    if doc_type == DocType.RECEIPT_INSPECTION:
        parsed.receipt_inspection_no = extract_field_value(
            text, "驗收單號", REGEX_RECEIPT_INSPECTION_NO_VALUE
        )
        # 抽取供商資訊
        parsed.vendor_code, parsed.vendor_name = extract_vendor_info(text)

    # 採購單：額外抽取請購單號（用於建立對照表）
    if doc_type == DocType.PURCHASE_ORDER:
        parsed.purchase_request_no = extract_field_value(
            text, "請購單號", REGEX_PURCHASE_REQUEST_NO_VALUE
        )

    return parsed


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

    Args:
        text: PDF 文字內容
        marker: 標籤文字（如「採購單號」）
        value_regex: 值的正則表達式
        exclude: 要排除的值（用於區分格式相同的不同欄位）
    """
    lines = text.split("\n")

    # 找到所有包含標籤的行
    marker_indices = [i for i, line in enumerate(lines) if marker in line]

    for marker_idx in marker_indices:
        # 在標籤後的幾行尋找符合格式的值（PDF 提取時標籤和值可能相差較遠）
        for j in range(marker_idx, min(marker_idx + 25, len(lines))):
            line = lines[j].strip()
            if value_regex.match(line):
                # 排除指定的值
                if exclude and line == exclude:
                    continue
                return line

    return None


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


def merge_pdfs(pdf_paths: list[Path], output_path: Path) -> None:
    """合併多個 PDF 為一份"""
    merged = fitz.open()
    for pdf_path in pdf_paths:
        doc = fitz.open(pdf_path)
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
    count = 0
    for line in lines:
        line = line.strip()
        if REGEX_SEQUENCE_NO.match(line):
            count += 1
    return count


def find_purchase_order_page(pages: list[str]) -> str | None:
    """找到採購單頁面（含「採購日期:」的頁面）"""
    for page_text in pages:
        if "採購日期:" in page_text:
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
