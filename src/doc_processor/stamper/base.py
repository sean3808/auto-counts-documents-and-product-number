"""蓋章基礎功能模組"""

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class StampConfig:
    """印章配置"""

    x: float  # 左上角 x 座標 (pt)
    y: float  # 左上角 y 座標 (pt)
    target_width: float  # 目標寬度 (pt)
    target_height: float  # 目標高度 (pt)
