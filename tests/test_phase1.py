"""phase1 模組測試"""

from pathlib import Path
import shutil

import pytest
import fitz

from doc_processor.logger import ProcessLogger
from doc_processor.phase1 import run_phase1
from doc_processor.pdf_parser import DocType, ParsedDocument


def _write_pdf(path: Path, page_count: int) -> None:
    doc = fitz.open()
    for _ in range(page_count):
        doc.new_page()
    doc.save(path)
    doc.close()


class TestRunPhase1:
    """Phase 1 整合測試"""

    def test_merge_documents(self, fixtures_dir: Path, temp_output_dir: Path):
        """測試 PDF 合併"""
        logger = ProcessLogger(temp_output_dir)

        exit_code = run_phase1(fixtures_dir, temp_output_dir, logger)

        # 應該成功
        assert exit_code == 0

        # 檢查輸出檔案
        output_files = list(temp_output_dir.glob("*.pdf"))
        assert len(output_files) == 1

        # 檢查檔名格式
        output_name = output_files[0].name
        assert "1011412050003" in output_name
        assert "YC016" in output_name

    def test_empty_input(self, tmp_path: Path, temp_output_dir: Path):
        """測試空的 input 資料夾"""
        empty_input = tmp_path / "empty_input"
        empty_input.mkdir()

        logger = ProcessLogger(temp_output_dir)
        exit_code = run_phase1(empty_input, temp_output_dir, logger)

        # 沒有檔案應該回傳成功（沒有失敗）
        assert exit_code == 0

    def test_skip_corrupt_pdf(self, fixtures_dir: Path, tmp_path: Path, temp_output_dir: Path):
        """測試壞檔不影響其他檔案處理"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        for pdf_path in fixtures_dir.glob("*.pdf"):
            shutil.copy(pdf_path, input_dir / pdf_path.name)

        (input_dir / "bad.pdf").write_text("not a pdf", encoding="utf-8")

        logger = ProcessLogger(temp_output_dir)
        exit_code = run_phase1(input_dir, temp_output_dir, logger)

        assert exit_code == 1
        output_files = list(temp_output_dir.glob("*.pdf"))
        assert len(output_files) == 1

    def test_multi_order_pdf_split(
        self,
        tmp_path: Path,
        temp_output_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """測試同一 PDF 多採購單可拆分處理"""
        input_dir = tmp_path / "input"
        input_dir.mkdir()

        po_no_1 = "1011412100001"
        po_no_2 = "1011412100002"

        goods_receipt_path = input_dir / "進貨單-多頁.pdf"
        _write_pdf(goods_receipt_path, 2)

        receipt_inspection_path = input_dir / "進貨驗收單-多頁.pdf"
        _write_pdf(receipt_inspection_path, 2)

        def fake_parse_documents(pdf_path: Path) -> list[ParsedDocument]:
            if pdf_path.name.startswith("進貨單"):
                return [
                    ParsedDocument(
                        path=pdf_path,
                        doc_type=DocType.GOODS_RECEIPT,
                        text="",
                        page_index=0,
                        purchase_order_no=po_no_1,
                        goods_receipt_no=po_no_1,
                    ),
                    ParsedDocument(
                        path=pdf_path,
                        doc_type=DocType.GOODS_RECEIPT,
                        text="",
                        page_index=1,
                        purchase_order_no=po_no_2,
                        goods_receipt_no=po_no_2,
                    ),
                ]
            if pdf_path.name.startswith("進貨驗收單"):
                return [
                    ParsedDocument(
                        path=pdf_path,
                        doc_type=DocType.RECEIPT_INSPECTION,
                        text="",
                        page_index=0,
                        purchase_order_no=po_no_1,
                        receipt_inspection_no=po_no_1,
                        vendor_code="VC01",
                        vendor_name="測試商",
                    ),
                    ParsedDocument(
                        path=pdf_path,
                        doc_type=DocType.RECEIPT_INSPECTION,
                        text="",
                        page_index=1,
                        purchase_order_no=po_no_2,
                        receipt_inspection_no=po_no_2,
                        vendor_code="VC01",
                        vendor_name="測試商",
                    ),
                ]
            return []

        monkeypatch.setattr("doc_processor.phase1.parse_documents", fake_parse_documents)

        logger = ProcessLogger(temp_output_dir)
        exit_code = run_phase1(input_dir, temp_output_dir, logger)

        output_files = list(temp_output_dir.glob("*.pdf"))
        output_names = [f.name for f in output_files]

        assert exit_code == 0
        assert len(output_files) == 2
        assert any(po_no_1 in name for name in output_names)
        assert any(po_no_2 in name for name in output_names)
        assert all("VC01" in name for name in output_names)
