"""pdf_parser 模組測試"""

from pathlib import Path

import pytest

from doc_processor.pdf_parser import (
    BusinessCategory,
    DocType,
    count_document_numbers,
    count_sequence_numbers,
    detect_business_category,
    detect_doc_type,
    extract_purchase_order_no_from_filename,
    extract_purchase_order_no_from_goods_receipt_text,
    extract_purchase_order_nos_from_goods_receipt_pages,
    extract_text,
    extract_text_by_page,
    find_purchase_order_page,
    parse_document,
    parse_documents,
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


class TestDetectBusinessCategory:
    """業務類別判斷測試"""

    def test_textile_by_unit_yard(self):
        """單位包含「碼」識別為紡織類"""
        text = "品名: 彈性布料\n驗收數量: 100.00\n單位: 碼\n"
        assert detect_business_category(text) == BusinessCategory.TEXTILE

    def test_textile_by_product_name_embryo_cloth(self):
        """品名包含「胚布」識別為紡織類"""
        text = "品名: JAC胚布[J7X02]\n數量: 2500\n單位: KG\n"
        assert detect_business_category(text) == BusinessCategory.TEXTILE

    def test_textile_by_remark_cloth(self):
        """備註包含「布」識別為紡織類"""
        text = "備註: 每批布不得低於40碼，並請將每疋胚布完成套袋包裝\n"
        assert detect_business_category(text) == BusinessCategory.TEXTILE

    def test_dye_default_with_fax_number(self):
        """排除「傳真號碼：」干擾，一般化工染料識別為染料類"""
        text = "傳真號碼：02-26007686\n驗收單號：11501020016\n品名: SODIUM HYDROSULPHITE\n單位: KG\n"
        assert detect_business_category(text) == BusinessCategory.DYE

    def test_dye_empty_text(self):
        """空文字預設為染料類"""
        assert detect_business_category("") == BusinessCategory.DYE


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

        pages = extract_text_by_page(pdf_path)
        page = find_purchase_order_page(pages)

        assert page is not None
        assert "採購日期:" in page

    def test_find_page_with_vendor_keyword(self):
        """測試以廠商關鍵字找到採購單頁"""
        pages = ["無關內容", "廠商: ABC"]

        page = find_purchase_order_page(pages)

        assert page == "廠商: ABC"

    def test_find_page_with_vendor_signature_keyword(self):
        """測試以承製廠商簽回關鍵字找到採購單頁"""
        pages = ["無關內容", "承製廠商簽回"]

        page = find_purchase_order_page(pages)

        assert page == "承製廠商簽回"


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


class TestExtractPurchaseOrderFromGoodsReceiptPages:
    """進貨單頁採購單號抽取測試"""

    def test_extract_from_goods_receipt_pages(self, fixtures_dir: Path):
        """測試從進貨單頁抽取採購單號"""
        pdf_path = fixtures_dir / "進貨單_1南京.pdf"
        if not pdf_path.exists():
            pytest.skip("進貨單樣本不存在")

        pages = extract_text_by_page(pdf_path)
        results = extract_purchase_order_nos_from_goods_receipt_pages(pages)

        assert results == {"1011412050003"}

    def test_extract_when_goods_receipt_no_matches(self):
        """測試採購單號與單據號碼相同時仍可抽取"""
        purchase_order_no = "1011412100001"
        text = f"單據號碼:\n{purchase_order_no}\n採購單號:\n{purchase_order_no}\n"

        result = extract_purchase_order_no_from_goods_receipt_text(text)

        assert result == purchase_order_no


class TestParseDocuments:
    """逐頁解析測試"""

    def test_parse_documents_multi_order(self, monkeypatch: pytest.MonkeyPatch):
        """測試同一 PDF 內多採購單逐頁解析"""
        po_no_1 = "1011412100001"
        po_no_2 = "1011412100002"
        pages = [
            f"採購單號:\n{po_no_1}\n驗收單號:\n{po_no_1}\n",
            f"採購單號:\n{po_no_2}\n驗收單號:\n{po_no_2}\n",
        ]

        def fake_extract_text_by_page(_: Path) -> list[str]:
            return pages

        monkeypatch.setattr(
            "doc_processor.pdf_parser.extract_text_by_page",
            fake_extract_text_by_page,
        )

        docs = parse_documents(Path("進貨驗收單-多頁.pdf"))

        assert [doc.purchase_order_no for doc in docs] == [po_no_1, po_no_2]
        assert [doc.page_index for doc in docs] == [0, 1]

    def test_group_contiguous_pages_for_same_order(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """測試同採購單連續頁合併"""
        po_no_1 = "1011412100001"
        po_no_2 = "1011412100002"
        pages = [
            f"採購單號:\n{po_no_1}\n頁 次:\n1 / 2\n",
            f"採購單號:\n{po_no_1}\n頁 次:\n2 / 2\n",
            f"採購單號:\n{po_no_2}\n頁 次:\n1 / 1\n",
        ]

        def fake_extract_text_by_page(_: Path) -> list[str]:
            return pages

        monkeypatch.setattr(
            "doc_processor.pdf_parser.extract_text_by_page",
            fake_extract_text_by_page,
        )

        docs = parse_documents(Path("採購單-多頁.pdf"))

        assert len(docs) == 2
        assert docs[0].purchase_order_no == po_no_1
        assert docs[0].page_indices == [0, 1]
        assert docs[1].purchase_order_no == po_no_2
        assert docs[1].page_indices == [2]
