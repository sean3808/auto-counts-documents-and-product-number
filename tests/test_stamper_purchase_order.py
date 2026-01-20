"""採購單蓋章模組測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.stamper.purchase_order import (
    STAMP_CONFIG_HANDLER,
    VENDOR_STAMP_X,
    VENDOR_STAMP_Y,
    stamp_purchase_order,
)


class TestPurchaseOrderStampConfigs:
    """採購單印章配置測試"""

    def test_handler_stamp_config(self):
        """測試承辦人印章配置"""
        assert STAMP_CONFIG_HANDLER.x == pytest.approx(335.6, rel=0.1)
        assert STAMP_CONFIG_HANDLER.y == pytest.approx(729.8, rel=0.1)

    def test_vendor_stamp_position(self):
        """測試承製廠商印章位置常數"""
        assert VENDOR_STAMP_X == pytest.approx(382.7, rel=0.1)
        assert VENDOR_STAMP_Y == pytest.approx(612.6, rel=0.1)


class TestStampPurchaseOrder:
    """stamp_purchase_order 函式測試"""

    @pytest.fixture
    def sample_pdf(self, tmp_path: Path) -> Path:
        """建立測試用採購單 PDF"""
        pdf_path = tmp_path / "採購單~1011501020005.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "供商代號：TW111")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def stamps_dir(self, tmp_path: Path) -> Path:
        """建立測試用印章資料夾"""
        stamps = tmp_path / "stamps"
        stamps.mkdir()
        # 建立個人章
        handler_stamp = Image.new("RGBA", (106, 56), (255, 0, 0, 128))
        handler_stamp.save(stamps / "雅萍.png")
        # 建立供應商章（直接用供商代碼命名）
        vendor_stamp = Image.new("RGBA", (395, 308), (0, 255, 0, 128))
        vendor_stamp.save(stamps / "TW111.png")
        return stamps

    def test_stamp_purchase_order_with_vendor(
        self, sample_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試採購單蓋章（含供應商章）"""
        output_path = tmp_path / "output.pdf"

        stamp_purchase_order(
            input_path=sample_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            vendor_code="TW111",
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應有 2 個印章：承辦人 + 供應商
        assert len(images) == 2

    def test_stamp_purchase_order_without_vendor(
        self, sample_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試採購單蓋章（無供應商章）"""
        output_path = tmp_path / "output.pdf"

        stamp_purchase_order(
            input_path=sample_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            vendor_code=None,
        )

        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應只有 1 個印章：承辦人
        assert len(images) == 1
