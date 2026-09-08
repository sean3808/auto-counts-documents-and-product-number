"""進貨驗收單蓋章模組測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.stamper.receiving import (
    STAMP_CONFIG_CREATOR,
    STAMP_CONFIG_WAREHOUSE,
    stamp_receiving,
)


class TestReceivingStampConfigs:
    """進貨驗收單印章配置測試"""

    def test_warehouse_stamp_config(self):
        """測試倉管人員印章配置"""
        assert STAMP_CONFIG_WAREHOUSE.x == pytest.approx(176.1, rel=0.1)
        assert STAMP_CONFIG_WAREHOUSE.y == pytest.approx(743.3, rel=0.1)

    def test_creator_stamp_config(self):
        """測試製單人員印章配置（基準座標與尺寸）"""
        assert STAMP_CONFIG_CREATOR.x == pytest.approx(508.2, abs=0.01)
        assert STAMP_CONFIG_CREATOR.y == pytest.approx(743.8, abs=0.01)
        assert STAMP_CONFIG_CREATOR.target_width == pytest.approx(32.1, abs=0.01)
        assert STAMP_CONFIG_CREATOR.target_height == pytest.approx(17.3, abs=0.01)


class TestStampReceiving:
    """stamp_receiving 函式測試"""

    @pytest.fixture
    def sample_pdf(self, tmp_path: Path) -> Path:
        """建立測試用進貨驗收單 PDF"""
        pdf_path = tmp_path / "進貨驗收單~採單1011501020005.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def stamps_dir(self, tmp_path: Path) -> Path:
        """建立測試用印章資料夾"""
        stamps = tmp_path / "stamps"
        stamps.mkdir()
        # 建立個人章
        warehouse_stamp = Image.new("RGBA", (99, 190), (255, 0, 0, 128))
        warehouse_stamp.save(stamps / "簡銘佑.png")
        creator_stamp = Image.new("RGBA", (106, 56), (0, 255, 0, 128))
        creator_stamp.save(stamps / "雅萍.png")
        return stamps

    def test_stamp_receiving(
        self, sample_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試進貨驗收單蓋章"""
        output_path = tmp_path / "output.pdf"

        stamp_receiving(
            input_path=sample_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應有 2 個印章：倉管人員 + 製單人員
        assert len(images) == 2
