"""Phase 0 蓋章階段測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.phase0 import run_phase0
from doc_processor.logger import ProcessLogger


class TestRunPhase0:
    """run_phase0 函式測試"""

    @pytest.fixture
    def setup_dirs(self, tmp_path: Path):
        """建立測試用資料夾結構"""
        input_dir = tmp_path / "input"
        output_dir = tmp_path / "temp" / "stamped"
        stamps_dir = tmp_path / "stamps"
        log_dir = tmp_path / "logs"

        input_dir.mkdir(parents=True)
        output_dir.mkdir(parents=True)
        stamps_dir.mkdir(parents=True)
        log_dir.mkdir(parents=True)

        # 建立測試用印章
        handler_stamp = Image.new("RGBA", (106, 56), (255, 0, 0, 128))
        handler_stamp.save(stamps_dir / "雅萍.png")

        warehouse_stamp = Image.new("RGBA", (99, 60), (0, 255, 0, 128))
        warehouse_stamp.save(stamps_dir / "簡銘佑.png")

        vendor_stamp = Image.new("RGBA", (200, 150), (0, 0, 255, 128))
        vendor_stamp.save(stamps_dir / "TW111.png")

        return {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "stamps_dir": stamps_dir,
            "log_dir": log_dir,
        }

    @pytest.fixture
    def sample_purchase_order(self, setup_dirs) -> Path:
        """建立測試用採購單 PDF"""
        pdf_path = setup_dirs["input_dir"] / "採購單~test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "TW111")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def sample_receiving(self, setup_dirs) -> Path:
        """建立測試用進貨驗收單 PDF"""
        pdf_path = setup_dirs["input_dir"] / "進貨驗收單~test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    def test_phase0_empty_input(self, setup_dirs):
        """測試空 input 資料夾"""
        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )
        # 空資料夾應回傳成功
        assert result == 0

    def test_phase0_purchase_order(self, setup_dirs, sample_purchase_order):
        """測試採購單蓋章"""
        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )

        assert result == 0
        output_file = setup_dirs["output_dir"] / "採購單~test.pdf"
        assert output_file.exists()

        # 驗證有蓋章
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) >= 1

    def test_phase0_receiving(self, setup_dirs, sample_receiving):
        """測試進貨驗收單蓋章"""
        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )

        assert result == 0
        output_file = setup_dirs["output_dir"] / "進貨驗收單~test.pdf"
        assert output_file.exists()

        # 驗證有蓋章
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 2  # 倉管章 + 製單章
