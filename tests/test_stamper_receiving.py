"""進貨驗收單蓋章模組測試"""

from pathlib import Path

import fitz
import pytest
from PIL import Image

from doc_processor.stamper.receiving import (
    DEFAULT_INSPECTION_STAMP,
    DEFAULT_TEXTILE_WAREHOUSE_STAMP,
    DEFAULT_WAREHOUSE_STAMP,
    INSPECTION_BASE_Y,
    INSPECTION_MAX_Y,
    STAMP_CONFIG_CREATOR,
    STAMP_CONFIG_INSPECTION,
    STAMP_CONFIG_WAREHOUSE,
    calculate_inspection_stamp_y,
    get_inspection_stamp_config,
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

    def test_inspection_stamp_config(self):
        """測試進料檢驗章配置（基準座標、尺寸與免去背設定）"""
        assert STAMP_CONFIG_INSPECTION.x == pytest.approx(40.5, abs=0.01)
        assert STAMP_CONFIG_INSPECTION.y == pytest.approx(270.4, abs=0.01)
        assert STAMP_CONFIG_INSPECTION.target_width == pytest.approx(221.4, abs=0.01)
        assert STAMP_CONFIG_INSPECTION.target_height == pytest.approx(166.7, abs=0.01)
        assert STAMP_CONFIG_INSPECTION.remove_background is False

    def test_default_inspection_stamp(self):
        """測試預設進料檢驗章檔名"""
        assert DEFAULT_INSPECTION_STAMP == "紡織進料檢.png"

    def test_default_warehouse_stamp(self):
        """測試預設染料類倉管章檔名"""
        assert DEFAULT_WAREHOUSE_STAMP == "簡銘佑.png"

    def test_default_textile_warehouse_stamp(self):
        """測試預設紡織類倉管章檔名"""
        assert DEFAULT_TEXTILE_WAREHOUSE_STAMP == "莊宛恬.png"


class TestStampReceiving:
    """stamp_receiving 函式測試"""

    @pytest.fixture
    def dye_pdf(self, tmp_path: Path) -> Path:
        """建立染料類進貨驗收單 PDF"""
        pdf_path = tmp_path / "進貨驗收單~染料.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單\n品名: SODIUM HYDROSULPHITE\n單位: KG\n")
        doc.save(pdf_path)
        doc.close()
        return pdf_path

    @pytest.fixture
    def textile_pdf(self, tmp_path: Path) -> Path:
        """建立紡織類進貨驗收單 PDF"""
        pdf_path = tmp_path / "進貨驗收單~紡織.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單\n品名: JAC胚布[J7X02]\n單位: 碼\n")
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
        textile_warehouse_stamp = Image.new("RGBA", (99, 190), (255, 0, 0, 128))
        textile_warehouse_stamp.save(stamps / "莊宛恬.png")
        creator_stamp = Image.new("RGBA", (106, 56), (0, 255, 0, 128))
        creator_stamp.save(stamps / "雅萍.png")
        # 建立進料檢驗章（白色背景表格）
        inspection_stamp = Image.new("RGB", (700, 470), (255, 255, 255))
        inspection_stamp.save(stamps / "紡織進料檢.png")
        return stamps

    def test_stamp_receiving_dye(
        self, dye_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試染料類進貨驗收單蓋章（倉管章 + 製單章）"""
        output_path = tmp_path / "output_dye.pdf"

        stamp_receiving(
            input_path=dye_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            is_textile=False,
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應有 2 個印章：倉管人員 + 製單人員
        assert len(images) == 2

    def test_stamp_receiving_textile(
        self, textile_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試紡織類進貨驗收單蓋章（進料檢驗章 + 莊宛恬倉管章 + 製單章）"""
        output_path = tmp_path / "output_textile.pdf"

        stamp_receiving(
            input_path=textile_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            is_textile=True,
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        # 應有 3 個印章：進料檢驗章 + 莊宛恬倉管章 + 製單人員
        assert len(images) == 3

    def test_stamp_receiving_textile_missing_warehouse_stamp(
        self, textile_pdf: Path, stamps_dir: Path, tmp_path: Path
    ):
        """測試缺少莊宛恬印章時優雅降級（僅蓋進料檢驗章與製單章）"""
        (stamps_dir / "莊宛恬.png").unlink()
        output_path = tmp_path / "output_textile_missing.pdf"

        stamp_receiving(
            input_path=textile_pdf,
            output_path=output_path,
            stamps_dir=stamps_dir,
            is_textile=True,
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 2

    @pytest.mark.parametrize("item_count,expected_mode", [
        (1, "base"),
        (2, "base"),
        (3, "shifted"),
        (8, "clamped"),
    ])
    def test_stamp_receiving_textile_item_counts(
        self, tmp_path: Path, stamps_dir: Path, item_count: int, expected_mode: str
    ):
        """測試紡織類進貨驗收單蓋章支援 1、2、3、8 項品項動態定位"""
        pdf_path = create_textile_receiving_pdf(
            tmp_path, item_count=item_count, filename=f"receiving_{item_count}.pdf"
        )
        output_path = tmp_path / f"output_{item_count}.pdf"

        stamp_receiving(
            input_path=pdf_path,
            output_path=output_path,
            stamps_dir=stamps_dir,
            is_textile=True,
        )

        assert output_path.exists()
        doc = fitz.open(output_path)
        page = doc[0]
        images = page.get_images()
        assert len(images) == 3

        img_rects = [page.get_image_rects(img[0])[0] for img in images]
        inspection_rects = [r for r in img_rects if r.width > 100]
        assert len(inspection_rects) == 1
        r = inspection_rects[0]

        if expected_mode == "base":
            assert r.y0 == pytest.approx(INSPECTION_BASE_Y, abs=0.01)
        elif expected_mode == "shifted":
            assert r.y0 > INSPECTION_BASE_Y
            assert r.y0 == pytest.approx(352.2, abs=5.0)
        elif expected_mode == "clamped":
            assert r.y0 == pytest.approx(INSPECTION_MAX_Y, abs=0.01)
            assert r.y1 <= 730.01
        doc.close()


def create_textile_receiving_pdf(
    tmp_path: Path, item_count: int, filename: str = "進貨驗收單~test.pdf"
) -> Path:
    """建立包含指定品項數量之紡織類進貨驗收單 PDF"""
    pdf_path = tmp_path / filename
    doc = fitz.open()
    page = doc.new_page(width=612, height=791)
    page.insert_text((235, 40), "台灣業旺股份有限公司", fontname="china-t")
    page.insert_text((270, 60), "進貨驗收單", fontname="china-t")
    page.insert_text((17, 90), "供商代號：GL012", fontname="china-t")
    page.insert_text((17, 110), "供商簡稱：金利多企", fontname="china-t")
    page.insert_text(
        (17, 165),
        "序號 產品代號 品名 採購數量 收貨數量 驗收數量 驗退數量單位 驗收日 庫別",
        fontname="china-t",
    )
    page.insert_text((484, 165), "碼", fontname="china-t")

    y = 180
    for i in range(1, item_count + 1):
        seq_str = f"{i:04d}"
        page.insert_text(
            (17, y),
            f"{seq_str} WG7X0{i} JAC胚布[J7X0{i}] 2,500.0000 1,479.0000 1,479.0000 0.0000 碼 115/09/02 東齊",
            fontname="china-t",
        )
        page.insert_text((48, y + 20), f"註:對方品名-布種_{i}", fontname="china-t")
        y += 50
    page.insert_text((48, y), "以下空白", fontname="china-t")

    page.insert_text(
        (17, 745),
        "主　管 倉　管： 人　員 倉　管： 主　管 驗　收： 人　員 驗　收： 人　員 製　單：",
        fontname="china-t",
    )
    doc.save(pdf_path)
    doc.close()
    return pdf_path


class TestCalculateInspectionStampY:
    """進料檢驗章自適應垂直座標計算測試"""

    def test_adaptive_y_1_item_returns_base_y(self, tmp_path: Path):
        """單頁 1 項品項時維持基準座標 (y=270.4 pt)"""
        pdf_path = create_textile_receiving_pdf(tmp_path, item_count=1)
        doc = fitz.open(pdf_path)
        y = calculate_inspection_stamp_y(doc[0])
        doc.close()
        assert y == pytest.approx(INSPECTION_BASE_Y, abs=0.01)

    def test_adaptive_y_2_items_returns_base_y(self, tmp_path: Path):
        """單頁 2 項品項時維持基準座標 (y=270.4 pt)"""
        pdf_path = create_textile_receiving_pdf(tmp_path, item_count=2)
        doc = fitz.open(pdf_path)
        y = calculate_inspection_stamp_y(doc[0])
        doc.close()
        assert y == pytest.approx(INSPECTION_BASE_Y, abs=0.01)

    def test_adaptive_y_3_items_shifts_down(self, tmp_path: Path):
        """單頁 3 項品項時向下順推至品項內容底緣下方 +20 pt"""
        pdf_path = create_textile_receiving_pdf(tmp_path, item_count=3)
        doc = fitz.open(pdf_path)
        y = calculate_inspection_stamp_y(doc[0])
        doc.close()
        assert y > INSPECTION_BASE_Y
        assert y == pytest.approx(352.2, abs=5.0)

    def test_adaptive_y_8_items_clamps_at_max_y(self, tmp_path: Path):
        """密集品項（8 項）時觸發上限截斷 (y <= 563.3 pt)，確保底緣在 730 pt 之前且不侵犯簽核欄 (y=735.5 pt)"""
        pdf_path = create_textile_receiving_pdf(tmp_path, item_count=8)
        doc = fitz.open(pdf_path)
        y = calculate_inspection_stamp_y(doc[0])
        doc.close()
        assert y == pytest.approx(INSPECTION_MAX_Y, abs=0.01)
        assert y + STAMP_CONFIG_INSPECTION.target_height <= 730.01

    def test_adaptive_y_empty_or_no_items(self, tmp_path: Path):
        """無品項頁面時維持基準座標 (y=270.4 pt)"""
        pdf_path = tmp_path / "empty.pdf"
        doc = fitz.open()
        page = doc.new_page(width=612, height=791)
        page.insert_text((100, 100), "進貨驗收單", fontname="china-t")
        doc.save(pdf_path)
        doc.close()

        doc = fitz.open(pdf_path)
        y = calculate_inspection_stamp_y(doc[0])
        doc.close()
        assert y == pytest.approx(INSPECTION_BASE_Y, abs=0.01)

    def test_get_inspection_stamp_config(self, tmp_path: Path):
        """測試 get_inspection_stamp_config 回傳包含動態 y 的 StampConfig"""
        pdf_path = create_textile_receiving_pdf(tmp_path, item_count=3)
        doc = fitz.open(pdf_path)
        config = get_inspection_stamp_config(doc[0])
        doc.close()
        assert config.x == pytest.approx(40.5, abs=0.01)
        assert config.y > 270.4
        assert config.target_width == pytest.approx(221.4, abs=0.01)
        assert config.target_height == pytest.approx(166.7, abs=0.01)
        assert config.remove_background is False

