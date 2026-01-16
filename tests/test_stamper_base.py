"""stamper.base 模組測試"""

from pathlib import Path

import pytest
from PIL import Image

from doc_processor.stamper.base import StampConfig, find_vendor_stamp


class TestStampConfig:
    """StampConfig dataclass 測試"""

    def test_stamp_config_creation(self):
        """測試建立 StampConfig"""
        config = StampConfig(
            x=100.0,
            y=200.0,
            target_width=30.0,
            target_height=17.0,
        )
        assert config.x == 100.0
        assert config.y == 200.0
        assert config.target_width == 30.0
        assert config.target_height == 17.0


class TestScaleImageToFit:
    """scale_image_to_fit 函式測試"""

    def test_scale_wider_image(self):
        """測試較寬的圖片（以寬度為準縮放）"""
        from doc_processor.stamper.base import scale_image_to_fit

        # 原始 200x100，目標框 100x100 → 縮放為 100x50
        new_w, new_h = scale_image_to_fit(200, 100, 100, 100)
        assert new_w == 100.0
        assert new_h == 50.0

    def test_scale_taller_image(self):
        """測試較高的圖片（以高度為準縮放）"""
        from doc_processor.stamper.base import scale_image_to_fit

        # 原始 100x200，目標框 100x100 → 縮放為 50x100
        new_w, new_h = scale_image_to_fit(100, 200, 100, 100)
        assert new_w == 50.0
        assert new_h == 100.0

    def test_scale_same_ratio(self):
        """測試相同比例"""
        from doc_processor.stamper.base import scale_image_to_fit

        # 原始 200x100，目標框 100x50 → 縮放為 100x50
        new_w, new_h = scale_image_to_fit(200, 100, 100, 50)
        assert new_w == 100.0
        assert new_h == 50.0

    def test_scale_smaller_image(self):
        """測試已經小於目標的圖片（不放大）"""
        from doc_processor.stamper.base import scale_image_to_fit

        # 原始 50x25，目標框 100x100 → 保持 50x25
        new_w, new_h = scale_image_to_fit(50, 25, 100, 100)
        assert new_w == 50.0
        assert new_h == 25.0


class TestFindVendorStamp:
    """find_vendor_stamp 函式測試"""

    @pytest.fixture
    def stamps_dir(self, tmp_path: Path) -> Path:
        """建立測試用印章資料夾"""
        stamps = tmp_path / "stamps"
        stamps.mkdir()
        # 建立測試用印章檔案（直接用供商代碼命名）
        for name in ["TW111.png", "TW113.png", "HE058.png"]:
            img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
            img.save(stamps / name)
        return stamps

    def test_find_existing_vendor_stamp(self, stamps_dir: Path):
        """測試找到存在的供應商印章"""
        result = find_vendor_stamp("TW111", stamps_dir)
        assert result is not None
        assert result.name == "TW111.png"

    def test_find_nonexistent_vendor_stamp(self, stamps_dir: Path):
        """測試找不到供應商印章"""
        result = find_vendor_stamp("XX999", stamps_dir)
        assert result is None

    def test_find_vendor_stamp_case_insensitive(self, stamps_dir: Path):
        """測試供商代號不區分大小寫"""
        result = find_vendor_stamp("tw111", stamps_dir)
        assert result is not None
        assert result.stem.upper() == "TW111"

    def test_find_vendor_stamp_jpg(self, stamps_dir: Path):
        """測試 JPG 格式印章"""
        # 建立 JPG 格式印章
        img = Image.new("RGB", (100, 100), (255, 0, 0))
        img.save(stamps_dir / "EL037.jpg")

        result = find_vendor_stamp("EL037", stamps_dir)
        assert result is not None
        assert result.name == "EL037.jpg"

    def test_find_vendor_stamp_legacy_format(self, stamps_dir: Path):
        """測試舊格式印章（{代碼}-{名稱}.png）"""
        # 建立舊格式印章
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        img.save(stamps_dir / "CH058-長興隆裕.png")

        result = find_vendor_stamp("CH058", stamps_dir)
        assert result is not None
        assert result.name == "CH058-長興隆裕.png"
