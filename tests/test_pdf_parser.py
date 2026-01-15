"""pdf_parser 模組測試"""

from pathlib import Path

import pytest

from doc_processor.pdf_parser import (
    DocType,
    count_document_numbers,
    count_sequence_numbers,
    detect_doc_type,
    extract_purchase_order_no_from_filename,
    extract_text,
    find_purchase_order_page,
    parse_document,
)


class TestDetectDocType:
    """單別判斷測試"""

    def test_purchase_order(self):
        assert detect_doc_type("採購單~1-南京.pdf") == DocType.PURCHASE_ORDER

    def test_purchase_request(self):
        assert detect_doc_type("請購單~1南京.pdf") == DocType.PURCHASE_REQUEST

    def test_goods_receipt(self):
        assert detect_doc_type("進貨單_1南京.pdf") == DocType.GOODS_RECEIPT

    def test_receipt_inspection(self):
        assert detect_doc_type("進貨驗收單~2-南京.pdf") == DocType.RECEIPT_INSPECTION

    def test_receipt_inspection_before_goods_receipt(self):
        """進貨驗收單應該先於進貨單判斷"""
        assert detect_doc_type("進貨驗收單xxx.pdf") == DocType.RECEIPT_INSPECTION

    def test_unknown(self):
        assert detect_doc_type("unknown.pdf") == DocType.UNKNOWN


class TestParseDocument:
    """PDF 解析測試"""

    def test_parse_goods_receipt(self, fixtures_dir: Path):
        """測試進貨單解析"""
        pdf_path = fixtures_dir / "進貨單_1南京.pdf"
        if not pdf_path.exists():
            pytest.skip("進貨單樣本不存在")

        doc = parse_document(pdf_path)

        assert doc.doc_type == DocType.GOODS_RECEIPT
        assert doc.purchase_order_no == "1011412050003"
        assert doc.goods_receipt_no is not None

    def test_parse_receipt_inspection(self, fixtures_dir: Path):
        """測試進貨驗收單解析"""
        pdf_path = fixtures_dir / "進貨驗收單~2-南京.pdf"
        if not pdf_path.exists():
            pytest.skip("進貨驗收單樣本不存在")

        doc = parse_document(pdf_path)

        assert doc.doc_type == DocType.RECEIPT_INSPECTION
        assert doc.purchase_order_no == "1011412050003"
        assert doc.vendor_code == "YC016"
        assert doc.vendor_name == "南京英誠"

    def test_parse_purchase_order(self, fixtures_dir: Path):
        """測試採購單解析"""
        pdf_path = fixtures_dir / "採購單~1-南京改數量.pdf"
        if not pdf_path.exists():
            pytest.skip("採購單樣本不存在")

        doc = parse_document(pdf_path)

        assert doc.doc_type == DocType.PURCHASE_ORDER
        assert doc.purchase_order_no == "1011412050003"
        assert doc.purchase_request_no == "1A11412050007"

    def test_parse_purchase_request(self, fixtures_dir: Path):
        """測試請購單解析"""
        pdf_path = fixtures_dir / "請購單~1南京改數量.pdf"
        if not pdf_path.exists():
            pytest.skip("請購單樣本不存在")

        doc = parse_document(pdf_path)

        assert doc.doc_type == DocType.PURCHASE_REQUEST
        assert doc.purchase_request_no == "1A11412050007"


class TestCountFunctions:
    """計數函式測試"""

    def test_count_document_numbers(self, fixtures_dir: Path):
        """測試張數計算"""
        pdf_path = fixtures_dir / "進貨單_1南京.pdf"
        if not pdf_path.exists():
            pytest.skip("進貨單樣本不存在")

        text = extract_text(pdf_path)
        count = count_document_numbers(text)

        assert count == 4  # 進貨單有 4 頁

    def test_count_sequence_numbers(self, fixtures_dir: Path):
        """測試支數計算"""
        pdf_path = fixtures_dir / "採購單~1-南京改數量.pdf"
        if not pdf_path.exists():
            pytest.skip("採購單樣本不存在")

        text = extract_text(pdf_path)
        count = count_sequence_numbers(text)

        assert count == 1  # 採購單只有一個序號 0001


class TestFindPurchaseOrderPage:
    """採購單頁面識別測試"""

    def test_find_page(self, fixtures_dir: Path):
        """測試找到採購單頁面"""
        pdf_path = fixtures_dir / "採購單~1-南京改數量.pdf"
        if not pdf_path.exists():
            pytest.skip("採購單樣本不存在")

        from doc_processor.pdf_parser import extract_text_by_page

        pages = extract_text_by_page(pdf_path)
        page = find_purchase_order_page(pages)

        assert page is not None
        assert "採購日期:" in page


class TestExtractFromFilename:
    """檔名抽取測試"""

    def test_extract_purchase_order_no(self):
        """測試從檔名抽取採購單號"""
        result = extract_purchase_order_no_from_filename(
            "1011412050003-YC016-南京英誠.pdf"
        )
        assert result == "1011412050003"

    def test_invalid_filename(self):
        """測試無效檔名"""
        result = extract_purchase_order_no_from_filename("invalid.pdf")
        assert result is None
