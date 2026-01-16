"""stamper.base 模組測試"""

from pathlib import Path

import pytest

from doc_processor.stamper.base import StampConfig


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
