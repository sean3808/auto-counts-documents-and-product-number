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
