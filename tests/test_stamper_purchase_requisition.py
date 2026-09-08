"""請購單蓋章模組測試"""

import pytest

from doc_processor.stamper.purchase_requisition import (
    DEFAULT_CREATOR_STAMP,
    STAMP_CONFIG_CREATOR,
)


class TestPurchaseRequisitionStampConfigs:
    """請購單印章配置測試"""

    def test_creator_stamp_config(self):
        """測試製表人員印章配置（基準座標與尺寸）"""
        assert STAMP_CONFIG_CREATOR.x == pytest.approx(452.9, abs=0.01)
        assert STAMP_CONFIG_CREATOR.y == pytest.approx(816.4, abs=0.01)
        assert STAMP_CONFIG_CREATOR.target_width == pytest.approx(32.1, abs=0.01)
        assert STAMP_CONFIG_CREATOR.target_height == pytest.approx(17.3, abs=0.01)

    def test_default_creator_stamp_name(self):
        """測試預設印章檔名"""
        assert DEFAULT_CREATOR_STAMP == "雅萍.png"
