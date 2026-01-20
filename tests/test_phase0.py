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

    def test_phase0_missing_stamps_folder(self, setup_dirs, sample_purchase_order):
        """測試印章資料夾不存在時應複製 PDF"""
        import shutil

        shutil.rmtree(setup_dirs["stamps_dir"])  # 移除印章資料夾
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

        # 驗證沒有蓋章（只是複製）
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 0

    def test_phase0_goods_receipt_stamped(self, setup_dirs):
        """測試進貨單應蓋章"""
        pdf_path = setup_dirs["input_dir"] / "進貨單~test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "進貨單")
        doc.save(pdf_path)
        doc.close()

        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )
        assert result == 0
        output_file = setup_dirs["output_dir"] / "進貨單~test.pdf"
        assert output_file.exists()

        # 驗證有蓋章（製表章）
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 1  # 應有 1 個印章（雅萍章）

    def test_phase0_purchase_requisition_stamped(self, setup_dirs):
        """測試請購單應蓋章"""
        pdf_path = setup_dirs["input_dir"] / "請購單~test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "請購單")
        doc.save(pdf_path)
        doc.close()

        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )
        assert result == 0
        output_file = setup_dirs["output_dir"] / "請購單~test.pdf"
        assert output_file.exists()

        # 驗證有蓋章（製表章）
        doc = fitz.open(output_file)
        images = doc[0].get_images()
        doc.close()
        assert len(images) == 1  # 應有 1 個印章（雅萍章）

    def test_phase0_partial_failure(self, setup_dirs, sample_purchase_order):
        """測試部分失敗時應回傳 1"""
        # 建立一個損壞的 PDF
        corrupt_pdf = setup_dirs["input_dir"] / "進貨驗收單~corrupt.pdf"
        corrupt_pdf.write_bytes(b"not a pdf")

        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )
        assert result == 1  # 部分失敗


class TestVendorSpecialConfig:
    """供應商專用配置測試"""

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

        # TW111 供應商章（需要專用配置）
        vendor_stamp_tw111 = Image.new("RGBA", (200, 150), (0, 0, 255, 128))
        vendor_stamp_tw111.save(stamps_dir / "TW111.png")

        # TW113 供應商章（需要專用配置）
        vendor_stamp_tw113 = Image.new("RGBA", (200, 150), (0, 255, 255, 128))
        vendor_stamp_tw113.save(stamps_dir / "TW113.png")

        # AA001 供應商章（使用預設配置）
        vendor_stamp_aa001 = Image.new("RGBA", (200, 150), (255, 255, 0, 128))
        vendor_stamp_aa001.save(stamps_dir / "AA001.png")

        return {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "stamps_dir": stamps_dir,
            "log_dir": log_dir,
        }

    def test_tw111_uses_yaml_config(self, setup_dirs):
        """測試 TW111 使用 YAML 配置的尺寸"""
        from unittest.mock import patch
        from doc_processor.stamper.base import get_target_pt, load_stamps_config

        # 從 YAML 讀取期望尺寸
        config = load_stamps_config()
        tw111_size = config.vendors.get("TW111")
        assert tw111_size is not None, "TW111 應在 config/stamps.yaml 中有配置"
        expected_w, expected_h = get_target_pt(
            tw111_size.width_cm, tw111_size.height_cm, config.print_scale
        )

        # 建立 TW111 採購單
        pdf_path = setup_dirs["input_dir"] / "採購單~tw111_test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "TW111")
        doc.save(pdf_path)
        doc.close()

        # 追蹤 scale_image_to_fit 呼叫的目標尺寸
        captured_calls = []
        original_scale = __import__(
            "doc_processor.stamper.base", fromlist=["scale_image_to_fit"]
        ).scale_image_to_fit

        def mock_scale(img_w, img_h, target_w, target_h):
            captured_calls.append((target_w, target_h))
            return original_scale(img_w, img_h, target_w, target_h)

        with patch("doc_processor.phase0.scale_image_to_fit", side_effect=mock_scale):
            logger = ProcessLogger(setup_dirs["log_dir"])
            result = run_phase0(
                setup_dirs["input_dir"],
                setup_dirs["output_dir"],
                setup_dirs["stamps_dir"],
                logger,
            )

        assert result == 0

        # 驗證有呼叫從 YAML 計算出的尺寸
        tw111_config_used = any(
            abs(target_w - expected_w) < 1 and abs(target_h - expected_h) < 1
            for target_w, target_h in captured_calls
        )
        assert tw111_config_used, (
            f"TW111 應使用 YAML 配置計算的尺寸 ({expected_w:.1f}x{expected_h:.1f})，"
            f"實際呼叫：{captured_calls}"
        )

    def test_tw113_uses_yaml_config(self, setup_dirs):
        """測試 TW113 使用 YAML 配置的尺寸"""
        from unittest.mock import patch
        from doc_processor.stamper.base import get_target_pt, load_stamps_config

        # 從 YAML 讀取期望尺寸
        config = load_stamps_config()
        tw113_size = config.vendors.get("TW113")
        assert tw113_size is not None, "TW113 應在 config/stamps.yaml 中有配置"
        expected_w, expected_h = get_target_pt(
            tw113_size.width_cm, tw113_size.height_cm, config.print_scale
        )

        # 建立 TW113 採購單
        pdf_path = setup_dirs["input_dir"] / "採購單~tw113_test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "TW113")
        doc.save(pdf_path)
        doc.close()

        captured_calls = []
        original_scale = __import__(
            "doc_processor.stamper.base", fromlist=["scale_image_to_fit"]
        ).scale_image_to_fit

        def mock_scale(img_w, img_h, target_w, target_h):
            captured_calls.append((target_w, target_h))
            return original_scale(img_w, img_h, target_w, target_h)

        with patch("doc_processor.phase0.scale_image_to_fit", side_effect=mock_scale):
            logger = ProcessLogger(setup_dirs["log_dir"])
            result = run_phase0(
                setup_dirs["input_dir"],
                setup_dirs["output_dir"],
                setup_dirs["stamps_dir"],
                logger,
            )

        assert result == 0

        tw113_config_used = any(
            abs(target_w - expected_w) < 1 and abs(target_h - expected_h) < 1
            for target_w, target_h in captured_calls
        )
        assert tw113_config_used, (
            f"TW113 應使用 YAML 配置計算的尺寸 ({expected_w:.1f}x{expected_h:.1f})，"
            f"實際呼叫：{captured_calls}"
        )

    def test_unconfigured_vendor_skipped(self, setup_dirs):
        """測試未配置的供應商印章會被跳過（文件仍成功處理）"""
        # 建立 AA001 採購單（AA001 沒有在 YAML 中配置）
        pdf_path = setup_dirs["input_dir"] / "採購單~aa001_test.pdf"
        doc = fitz.open()
        page = doc.new_page(width=596, height=842)
        page.insert_text((100, 100), "採購單")
        page.insert_text((100, 150), "AA001")
        doc.save(pdf_path)
        doc.close()

        logger = ProcessLogger(setup_dirs["log_dir"])
        result = run_phase0(
            setup_dirs["input_dir"],
            setup_dirs["output_dir"],
            setup_dirs["stamps_dir"],
            logger,
        )

        # 文件仍被視為成功處理（跳過供應商章，繼續處理）
        assert result == 0, "文件應成功處理（供應商章被跳過）"

        # 檢查輸出的 PDF 只有承辦人章（沒有供應商章）
        output_path = setup_dirs["output_dir"] / "採購單~aa001_test.pdf"
        assert output_path.exists()
        with fitz.open(output_path) as out_doc:
            images = out_doc[0].get_images()
            # 應只有 1 個印章（承辦人章），因為供應商章因配置缺失被跳過
            assert len(images) == 1, "未配置的供應商印章應被跳過"
